"""
    to run the test
    python ~/ceph/qa/tasks/vstart_runner.py --run-all-tests tasks.cephfs.test_perf_counters
"""
import json
import logging

from tasks.cephfs.cephfs_test_case import CephFSTestCase

log = logging.getLogger(__name__)

# Published API contract for the 'client' perf section.
# Each entry is (field_name, expected_json_type) where:
#   'int'   → JSON integer  (add_u64 / add_u64_counter)
#   'float' → JSON number   (add_time plain — serialised unquoted as
#             "seconds.nanoseconds" by dump_format_unquoted, decoded by
#             Python's json module as float)
_CLIENT_COUNTER_CONTRACT = [
    # Samba-facing I/O op counts
    ('mdops',      'int'),
    ('rdops',      'int'),
    ('wrops',      'int'),
    # Rolling average latencies (add_time plain → unquoted decimal → float)
    ('mdavg',      'float'),
    ('readavg',    'float'),
    ('writeavg',   'float'),
    # Sum-of-squares accumulators (used to derive stddev)
    ('mdsqsum',    'int'),
    ('readsqsum',  'int'),
    ('writesqsum', 'int'),
]

_INT_COUNTER_FIELDS   = [f for f, t in _CLIENT_COUNTER_CONTRACT if t == 'int']
_FLOAT_COUNTER_FIELDS = [f for f, t in _CLIENT_COUNTER_CONTRACT if t == 'float']
_ALL_CONTRACT_FIELDS  = [f for f, _ in _CLIENT_COUNTER_CONTRACT]


class TestPerfCounters(CephFSTestCase):

    CLIENTS_REQUIRED = 1
    MDSS_REQUIRED = 1

    @staticmethod
    def _extract_json(raw):
        """
        Extract the first complete JSON object from *raw*.

        vstart prepends 'Using guessed paths ...' banner lines to stdout.
        ceph_get_perf_counters() returns multiple concatenated JSON blobs
        (one per perf module).  JSONDecoder.raw_decode() stops after the
        first complete value, which is the one we want.
        """
        idx = raw.find('{')
        if idx < 0:
            raise ValueError("No JSON object found in output: %.300s" % raw)
        obj, _ = json.JSONDecoder().raw_decode(raw, idx)
        return obj

    def _asok_perf_dump(self):
        """
        Query perf counters from the live ceph-fuse process via its admin
        socket.  Returns the parsed JSON dict.
        """
        return self.mount_a.admin_socket(['perf', 'dump'])

    def _call_get_perf_counters(self):
        """
        Spin up a fresh libcephfs handle via ctypes, call
        ceph_get_perf_counters(), and return the parsed JSON dict.

        The handle is independent of mount_a so its I/O counters start
        at zero.
        """
        pyscript = (
            "import ctypes, ctypes.util, sys, os\n"
            "lib_path = None\n"
            "for d in os.environ.get('LD_LIBRARY_PATH', '').split(':'):\n"
            "    candidate = os.path.join(d, 'libcephfs.so.2')\n"
            "    if os.path.exists(candidate):\n"
            "        lib_path = candidate\n"
            "        break\n"
            "if lib_path is None:\n"
            "    lib_path = ctypes.util.find_library('cephfs')\n"
            "if lib_path is None:\n"
            "    sys.exit('libcephfs.so not found')\n"
            "lib = ctypes.CDLL(lib_path)\n"
            "class CephMountInfo(ctypes.Structure): pass\n"
            "CephMountInfoP = ctypes.POINTER(CephMountInfo)\n"
            "lib.ceph_create.restype = ctypes.c_int\n"
            "lib.ceph_create.argtypes = [ctypes.POINTER(CephMountInfoP), ctypes.c_char_p]\n"
            "lib.ceph_conf_read_file.restype = ctypes.c_int\n"
            "lib.ceph_conf_read_file.argtypes = [CephMountInfoP, ctypes.c_char_p]\n"
            "lib.ceph_conf_parse_env.restype = ctypes.c_int\n"
            "lib.ceph_conf_parse_env.argtypes = [CephMountInfoP, ctypes.c_char_p]\n"
            "lib.ceph_mount.restype = ctypes.c_int\n"
            "lib.ceph_mount.argtypes = [CephMountInfoP, ctypes.c_char_p]\n"
            "lib.ceph_get_perf_counters.restype = ctypes.c_int\n"
            "lib.ceph_get_perf_counters.argtypes = [CephMountInfoP, ctypes.POINTER(ctypes.c_char_p)]\n"
            "lib.ceph_shutdown.restype = ctypes.c_int\n"
            "lib.ceph_shutdown.argtypes = [CephMountInfoP]\n"
            "cmount = CephMountInfoP()\n"
            "assert lib.ceph_create(ctypes.byref(cmount), None) == 0\n"
            "assert lib.ceph_conf_read_file(cmount, None) == 0\n"
            "assert lib.ceph_conf_parse_env(cmount, None) == 0\n"
            "assert lib.ceph_mount(cmount, b'/') == 0\n"
            "buf = ctypes.c_char_p()\n"
            "length = lib.ceph_get_perf_counters(cmount, ctypes.byref(buf))\n"
            "assert length > 0, 'ceph_get_perf_counters returned %d' % length\n"
            "result = buf.value.decode('utf-8', errors='replace')\n"
            "lib.ceph_shutdown(cmount)\n"
            "print(result)\n"
        )
        raw = self.mount_a.run_python(pyscript)
        return self._extract_json(raw)

    def _drop_caches(self):
        """
        Drop the kernel page cache so a subsequent read must go through
        the ceph-fuse process to the OSD, guaranteeing rdops increments.
        """
        self.mount_a.run_shell(
            ["sudo", "sysctl", "-w", "vm.drop_caches=3"],
            omit_sudo=False,
        )

    def test_capi_returns_valid_json(self):
        """
        ceph_get_perf_counters() must return a non-zero length and the
        buffer must contain a non-empty JSON object.
        """
        data = self._call_get_perf_counters()
        self.assertIsInstance(
            data, dict,
            "ceph_get_perf_counters() must return a JSON object; got %s" % type(data),
        )
        self.assertGreater(len(data), 0, "JSON object must not be empty")

    def test_asok_returns_valid_json(self):
        """
        ``ceph --admin-daemon <asok> perf dump`` must return a non-empty
        JSON object.
        """
        data = self._asok_perf_dump()
        self.assertIsInstance(
            data, dict,
            "admin-socket perf dump must return a JSON object; got %s" % type(data),
        )
        self.assertGreater(len(data), 0, "JSON object must not be empty")

    def test_capi_has_client_section(self):
        """
        The C API output must contain a top-level 'client' key.
        """
        data = self._call_get_perf_counters()
        self.assertIn(
            'client', data,
            "C API output missing 'client' section. "
            "Top-level keys present: %s" % sorted(data.keys()),
        )

    def test_asok_has_client_section(self):
        """
        The admin-socket output must contain a top-level 'client' key.
        """
        data = self._asok_perf_dump()
        self.assertIn(
            'client', data,
            "admin-socket output missing 'client' section. "
            "Top-level keys present: %s" % sorted(data.keys()),
        )

    def test_capi_client_section_has_all_contract_fields(self):
        """
        Every field in _CLIENT_COUNTER_CONTRACT must be present in the
        C API 'client' section.  Catches deleted or renamed counters.
        """
        client = self._call_get_perf_counters().get('client', {})
        for field in _ALL_CONTRACT_FIELDS:
            self.assertIn(
                field, client,
                "C API 'client' section is missing field '%s'. "
                "Fields present: %s" % (field, sorted(client.keys())),
            )

    def test_asok_client_section_has_all_contract_fields(self):
        """
        Every field in _CLIENT_COUNTER_CONTRACT must be present in the
        admin-socket 'client' section.  Catches deleted or renamed counters.
        """
        client = self._asok_perf_dump().get('client', {})
        for field in _ALL_CONTRACT_FIELDS:
            self.assertIn(
                field, client,
                "admin-socket 'client' section is missing field '%s'. "
                "Fields present: %s" % (field, sorted(client.keys())),
            )

    def test_capi_integer_counter_types(self):
        """
        Integer counters (add_u64) must serialise as JSON integers, not
        strings, floats, or nested objects.
        """
        client = self._call_get_perf_counters().get('client', {})
        for field in _INT_COUNTER_FIELDS:
            val = client[field]
            self.assertIsInstance(
                val, int,
                "C API: 'client.%s' must be a JSON integer, got %s (%r)"
                % (field, type(val).__name__, val),
            )
            # bool is a subclass of int in Python; reject it explicitly
            self.assertNotIsInstance(
                val, bool,
                "C API: 'client.%s' must not be a boolean" % field,
            )

    def test_asok_integer_counter_types(self):
        """
        Integer counters must be JSON integers in the admin-socket output.
        """
        client = self._asok_perf_dump().get('client', {})
        for field in _INT_COUNTER_FIELDS:
            val = client[field]
            self.assertIsInstance(
                val, int,
                "admin-socket: 'client.%s' must be a JSON integer, got %s (%r)"
                % (field, type(val).__name__, val),
            )
            self.assertNotIsInstance(
                val, bool,
                "admin-socket: 'client.%s' must not be a boolean" % field,
            )

    def test_capi_time_counter_types(self):
        """
        Time counters (add_time plain) are serialised unquoted by
        dump_format_unquoted and decoded as floats by Python's json
        module.  They must be float and non-negative.
        """
        client = self._call_get_perf_counters().get('client', {})
        for field in _FLOAT_COUNTER_FIELDS:
            val = client[field]
            self.assertIsInstance(
                val, float,
                "C API: 'client.%s' must be a JSON float (time counter), "
                "got %s (%r)" % (field, type(val).__name__, val),
            )
            self.assertGreaterEqual(
                val, 0.0,
                "C API: 'client.%s' must be non-negative, got %r" % (field, val),
            )

    def test_asok_time_counter_types(self):
        """
        Time counters must be floats in the admin-socket output.
        """
        client = self._asok_perf_dump().get('client', {})
        for field in _FLOAT_COUNTER_FIELDS:
            val = client[field]
            self.assertIsInstance(
                val, float,
                "admin-socket: 'client.%s' must be a JSON float (time counter), "
                "got %s (%r)" % (field, type(val).__name__, val),
            )
            self.assertGreaterEqual(
                val, 0.0,
                "admin-socket: 'client.%s' must be non-negative, got %r" % (field, val),
            )

    def test_capi_rdops_zero_on_fresh_mount(self):
        """
        A fresh libcephfs handle that has performed no read I/O must
        report rdops == 0.
        """
        client = self._call_get_perf_counters().get('client', {})
        rdops = client['rdops']
        self.assertEqual(
            rdops, 0,
            "rdops must be 0 on a fresh mount with no read I/O; got %d" % rdops,
        )

    def test_capi_wrops_zero_on_fresh_mount(self):
        """
        A fresh libcephfs handle that has performed no write I/O must
        report wrops == 0.
        """
        client = self._call_get_perf_counters().get('client', {})
        wrops = client['wrops']
        self.assertEqual(
            wrops, 0,
            "wrops must be 0 on a fresh mount with no write I/O; got %d" % wrops,
        )

    def test_capi_readavg_zero_when_no_reads(self):
        """
        When rdops == 0 the readavg field must be 0.0.
        The latency accumulator is only written after a read completes,
        so with no reads it must not have been touched.
        """
        client = self._call_get_perf_counters().get('client', {})
        if client['rdops'] != 0:
            self.skipTest("rdops=%d on fresh mount; zero-avg check not applicable"
                          % client['rdops'])
        self.assertEqual(
            client['readavg'], 0.0,
            "readavg must be 0.0 when rdops == 0; got %r" % client['readavg'],
        )

    def test_capi_writeavg_zero_when_no_writes(self):
        """
        When wrops == 0 the writeavg field must be 0.0.
        """
        client = self._call_get_perf_counters().get('client', {})
        if client['wrops'] != 0:
            self.skipTest("wrops=%d on fresh mount; zero-avg check not applicable"
                          % client['wrops'])
        self.assertEqual(
            client['writeavg'], 0.0,
            "writeavg must be 0.0 when wrops == 0; got %r" % client['writeavg'],
        )

    def test_capi_sqsums_zero_when_no_io(self):
        """
        readsqsum and writesqsum must be 0 when rdops/wrops is 0.
        """
        client = self._call_get_perf_counters().get('client', {})
        checks = [
            ('rdops', 'readsqsum'),
            ('wrops', 'writesqsum'),
        ]
        for ops_field, sqsum_field in checks:
            if client[ops_field] == 0:
                self.assertEqual(
                    client[sqsum_field], 0,
                    "'%s' must be 0 when %s == 0; got %d"
                    % (sqsum_field, ops_field, client[sqsum_field]),
                )

    def test_capi_and_asok_top_level_keys_match(self):
        """
        ceph_get_perf_counters() and admin-socket perf dump must return
        the same set of top-level section keys.
        """
        capi_keys = set(self._call_get_perf_counters().keys())
        asok_keys = set(self._asok_perf_dump().keys())
        self.assertEqual(
            capi_keys, asok_keys,
            "Top-level section keys differ between C API and admin-socket.\n"
            "  C API only : %s\n  asok only  : %s"
            % (sorted(capi_keys - asok_keys), sorted(asok_keys - capi_keys)),
        )

    def test_capi_and_asok_client_fields_match(self):
        """
        The 'client' section must have identical field names in both the
        C API and admin-socket outputs.
        """
        capi_client = set(self._call_get_perf_counters().get('client', {}).keys())
        asok_client = set(self._asok_perf_dump().get('client', {}).keys())
        self.assertEqual(
            capi_client, asok_client,
            "'client' field names differ between C API and admin-socket.\n"
            "  C API only : %s\n  asok only  : %s"
            % (sorted(capi_client - asok_client), sorted(asok_client - capi_client)),
        )

    def test_wrops_increments_after_write(self):
        """
        wrops must increase after writing data through the mounted
        filesystem.
        """
        before = self._asok_perf_dump().get('client', {}).get('wrops', 0)
        self.mount_a.write_n_mb("bb_write_test", 1)
        after = self._asok_perf_dump().get('client', {}).get('wrops', 0)

        log.info("wrops: %d -> %d", before, after)
        self.assertGreater(
            after, before,
            "wrops did not increase after writing 1 MiB (before=%d after=%d)"
            % (before, after),
        )

    def test_rdops_increments_after_read(self):
        """
        rdops must increase after reading data that is not in any cache.
        Both the kernel page cache and the ceph-fuse object cache are
        dropped first to force the read to go to the OSD.
        """
        self.mount_a.write_n_mb("bb_read_test", 1)
        self._drop_caches()

        before = self._asok_perf_dump().get('client', {}).get('rdops', 0)
        self.mount_a.run_shell(["dd", "if=bb_read_test", "of=/dev/null", "bs=1M"])
        after = self._asok_perf_dump().get('client', {}).get('rdops', 0)

        log.info("rdops: %d -> %d", before, after)
        self.assertGreater(
            after, before,
            "rdops did not increase after reading 1 MiB (before=%d after=%d)"
            % (before, after),
        )

    def test_mdops_increments_after_metadata_op(self):
        """
        mdops must increase after a metadata operation (mkdir).
        """
        before = self._asok_perf_dump().get('client', {}).get('mdops', 0)
        self.mount_a.run_shell(["mkdir", "bb_mdops_testdir"])
        after = self._asok_perf_dump().get('client', {}).get('mdops', 0)

        log.info("mdops: %d -> %d", before, after)
        self.assertGreater(
            after, before,
            "mdops did not increase after mkdir (before=%d after=%d)"
            % (before, after),
        )

    def test_readavg_nonzero_after_read(self):
        """
        After at least one read, readavg must be > 0.0 — a real latency
        must have been recorded.
        """
        self.mount_a.write_n_mb("bb_readavg_test", 1)
        self._drop_caches()
        self.mount_a.run_shell(["dd", "if=bb_readavg_test", "of=/dev/null", "bs=1M"])

        client = self._asok_perf_dump().get('client', {})
        self.assertGreater(
            client.get('rdops', 0), 0,
            "rdops still 0 after a forced read — readavg check is inconclusive",
        )
        self.assertGreater(
            client.get('readavg', 0.0), 0.0,
            "readavg is still 0.0 after %d read ops" % client.get('rdops', 0),
        )

    def test_writeavg_nonzero_after_write(self):
        """
        After at least one write, writeavg must be > 0.0.
        """
        self.mount_a.write_n_mb("bb_writeavg_test", 1)

        client = self._asok_perf_dump().get('client', {})
        self.assertGreater(
            client.get('wrops', 0), 0,
            "wrops still 0 after a write — writeavg check is inconclusive",
        )
        self.assertGreater(
            client.get('writeavg', 0.0), 0.0,
            "writeavg is still 0.0 after %d write ops" % client.get('wrops', 0),
        )

    def test_capi_and_asok_both_see_wrops_increment(self):
        """
        After writes, admin-socket must see wrops > 0 (live mount_a
        process) and the C API fresh handle must see wrops == 0 (no
        writes on that independent handle).
        """
        self.mount_a.write_n_mb("cross_wrops_test", 1)

        asok_client = self._asok_perf_dump().get('client', {})
        capi_client = self._call_get_perf_counters().get('client', {})

        log.info("asok wrops=%d  capi wrops=%d",
                 asok_client.get('wrops', -1), capi_client.get('wrops', -1))

        # admin-socket reflects mount_a's accumulated writes
        self.assertGreater(
            asok_client.get('wrops', 0), 0,
            "admin-socket wrops must be > 0 after writes",
        )
        # C API fresh handle: wrops starts at 0 then does a tiny MDS mount,
        # so wrops must still be 0 (no write I/O on the new handle)
        self.assertEqual(
            capi_client.get('wrops', -1), 0,
            "C API fresh handle must have wrops=0 (no writes on that handle); "
            "got %d" % capi_client.get('wrops', -1),
        )

    def test_capi_and_asok_client_field_types_agree(self):
        """
        For every field in _CLIENT_COUNTER_CONTRACT, the Python type of
        the value must be identical in both the C API and admin-socket
        outputs.
        """
        capi_client = self._call_get_perf_counters().get('client', {})
        asok_client = self._asok_perf_dump().get('client', {})

        for field in _ALL_CONTRACT_FIELDS:
            capi_val = capi_client.get(field)
            asok_val = asok_client.get(field)
            if capi_val is None or asok_val is None:
                continue  # missing-field tests cover this separately
            self.assertIs(
                type(capi_val), type(asok_val),
                "Type mismatch for 'client.%s': "
                "C API returned %s, admin-socket returned %s"
                % (field, type(capi_val).__name__, type(asok_val).__name__),
            )
