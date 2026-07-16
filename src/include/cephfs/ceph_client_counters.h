#ifndef CEPH_CLIENT_COUNTERS_H
#define CEPH_CLIENT_COUNTERS_H

#include <stdint.h>

/**
 * A latency measurement expressed as a running average.
 *
 * ns_sum  - cumulative nanoseconds across all recorded operations.
 * count   - number of operations recorded.
 *
 * Mean latency in nanoseconds: ns_sum / count  (when count > 0).
 */
struct ceph_latency {
  uint64_t ns_sum;
  uint64_t count;
};

/**
 * Structured client interface counters for consumption by external
 * consumers such as Samba.  All latency values are in nanoseconds.
 *
 * This is the STABLE, EXPLICIT tier of the client perf counter API.
 * Fields are named directly and accessed without any runtime lookup.
 * Use this on the I/O path where zero-overhead field access is required.
 *
 * Use ceph_get_client_counters() to obtain a heap-allocated snapshot
 * and ceph_free_client_counters() to release it.
 *
 * ABI stability: the struct size is fixed.  New fields are assigned
 * from the reserved[] bank at the end.  Callers must treat any field
 * beyond the ones they know about as zero.
 */
struct ceph_client_counters {

  /* --- I/O latency --- */
  struct ceph_latency read_latency;
  struct ceph_latency write_latency;
  struct ceph_latency metadata_latency;

  /* --- Per-op MDS latency --- */
  struct ceph_latency lat_create;
  struct ceph_latency lat_mkdir;
  struct ceph_latency lat_unlink;
  struct ceph_latency lat_rmdir;
  struct ceph_latency lat_rename;
  struct ceph_latency lat_setattr;

  /* --- I/O operation totals --- */
  /** Total number of read operations since mount. */
  uint64_t total_read_ops;
  /** Total bytes read since mount. */
  uint64_t total_read_bytes;
  /** Total number of write operations since mount. */
  uint64_t total_write_ops;
  /** Total bytes written since mount. */
  uint64_t total_write_bytes;

  /* --- Metadata request counts --- */
  uint64_t nr_metadata_requests;
  uint64_t nr_read_requests;
  uint64_t nr_write_requests;

  /* --- Capability stats --- */
  uint64_t cap_hits;
  uint64_t cap_misses;

  /* --- Dentry lease stats --- */
  uint64_t dlease_hits;
  uint64_t dlease_misses;
  /** Current number of dentries in the metadata cache. */
  uint64_t dentry_count;

  /* --- Open file / inode counts --- */
  uint64_t opened_files;
  uint64_t pinned_icaps;
  uint64_t opened_inodes;
  /** Total number of inodes tracked by the client. */
  uint64_t total_inodes;

  /* --- MDS cache / caps health --- */
  /** Number of inodes with caps currently being flushed to MDS. */
  uint64_t caps_flushing;
  /** Number of in-flight metadata requests not yet committed on MDS. */
  uint64_t unsafe_reqs;

  /* --- File locking --- */
  /** Total fcntl/flock locking operations. */
  uint64_t lock_ops;
  struct ceph_latency lock_latency;

  /* --- ObjectCacher local cache config --- */
  /** 1 if the ObjectCacher is active, 0 if disabled. */
  uint8_t  oc_enabled;
  /** Maximum total bytes the cache may hold (client_oc_size). */
  uint64_t oc_max_size;
  /** Maximum dirty bytes before writes are throttled (client_oc_max_dirty). */
  uint64_t oc_max_dirty;
  /** Maximum number of objects tracked in the cache (client_oc_max_objects). */
  uint64_t oc_max_objects;
  /** Current number of objects tracked in the cache LRU. */
  uint64_t oc_object_count;

  /* --- ObjectCacher local cache runtime state --- */
  int64_t  oc_stat_clean;
  int64_t  oc_stat_dirty;
  int64_t  oc_stat_rx;
  int64_t  oc_stat_tx;
  int64_t  oc_stat_missing;
  int64_t  oc_stat_dirty_waiting;

  /* --- Reserved padding for future ABI-compatible extension --- */
  /**
   * These fields are zeroed by ceph_get_client_counters() and must not be
   * read or written by callers.  New counter fields will be assigned from
   * this bank in future releases, keeping the struct size stable.
   */
  uint64_t reserved[32];
};

#endif /* CEPH_CLIENT_COUNTERS_H */
