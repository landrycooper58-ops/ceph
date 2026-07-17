// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:nil -*-
// vim: ts=8 sw=2 sts=2 expandtab

#ifndef CEPH_PERF_COUNTER_ENTRY_H
#define CEPH_PERF_COUNTER_ENTRY_H

#include <stdint.h>

enum ceph_perf_counter_type_flags {
  CEPH_PERF_NONE       = 0,
  CEPH_PERF_TIME       = 0x1,
  CEPH_PERF_U64        = 0x2,
  CEPH_PERF_LONGRUNAVG = 0x4,
  CEPH_PERF_COUNTER    = 0x8,
};

struct ceph_perf_counter_entry {
  const char *name;
  uint8_t     type;
  uint64_t    value_sum;
  uint64_t    value_count;
};

struct ceph_perf_counters_list {
  struct ceph_perf_counter_entry *entries;
  uint32_t nr_entries;
};

#endif /* CEPH_PERF_COUNTER_ENTRY_H */
