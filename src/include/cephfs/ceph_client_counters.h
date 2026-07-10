

#ifndef CEPH_CLIENT_COUNTERS_H
#define CEPH_CLIENT_COUNTERS_H

#include <stdint.h>

/**
 * Structured client interface counters for consumption by external
 * consumers such as Samba.  All latency values are in nanoseconds.
 * Use ceph_get_client_counters() to obtain a heap-allocated snapshot
 * and ceph_free_client_counters() to release it.
 */
struct ceph_client_counters {
  /* --- I/O latency (nanoseconds; sum / count for rolling average) --- */
  /** Cumulative nanoseconds spent in read data operations. */
  uint64_t read_latency_ns_sum;
  /** Number of read data operations recorded. */
  uint64_t read_latency_count;

  /** Cumulative nanoseconds spent in write data operations. */
  uint64_t write_latency_ns_sum;
  /** Number of write data operations recorded. */
  uint64_t write_latency_count;

  /** Cumulative nanoseconds spent in metadata (MDS) operations. */
  uint64_t metadata_latency_ns_sum;
  /** Number of metadata operations recorded. */
  uint64_t metadata_latency_count;

  /* --- Per-op MDS latency (ns sum + count pairs) --- */
  uint64_t lat_create_ns_sum;
  uint64_t lat_create_count;

  uint64_t lat_mkdir_ns_sum;
  uint64_t lat_mkdir_count;

  uint64_t lat_unlink_ns_sum;
  uint64_t lat_unlink_count;

  uint64_t lat_rmdir_ns_sum;
  uint64_t lat_rmdir_count;

  uint64_t lat_rename_ns_sum;
  uint64_t lat_rename_count;

  uint64_t lat_setattr_ns_sum;
  uint64_t lat_setattr_count;

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
  /** Number of capability cache hits. */
  uint64_t cap_hits;
  /** Number of capability cache misses. */
  uint64_t cap_misses;

  /* --- Dentry lease stats --- */
  /** Number of dentry lease cache hits. */
  uint64_t dlease_hits;
  /** Number of dentry lease cache misses. */
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
  /** Cumulative nanoseconds spent in lock operations (sum + count). */
  uint64_t lock_latency_ns_sum;
  uint64_t lock_latency_count;

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
  /** Bytes currently cached and clean. */
  int64_t  oc_stat_clean;
  /** Bytes currently dirty (written to cache, not yet flushed to OSD). */
  int64_t  oc_stat_dirty;
  /** Bytes in flight from OSD into cache (reads in progress). */
  int64_t  oc_stat_rx;
  /** Bytes in flight from cache to OSD (writes in progress). */
  int64_t  oc_stat_tx;
  /** Bytes not yet fetched from OSD. */
  int64_t  oc_stat_missing;
  /** Bytes blocked because the dirty limit is full. */
  int64_t  oc_stat_dirty_waiting;

  /* --- Reserved padding for future ABI-compatible extension --- */
  /**
   * These fields are zeroed by ceph_get_client_counters() and must not be
   * read or written by callers.  New counter fields will be assigned from
   * this bank in future releases, keeping the struct size stable.
   */
  uint64_t reserved[16];
};

#endif /* CEPH_CLIENT_COUNTERS_H */
