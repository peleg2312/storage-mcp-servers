---
name: powermax-performance
description: Analyse PowerMax performance for an array, storage group, host, FA port or director over a time window - response time, IOPS, throughput, utilization, cache, SRDF - with avg and max. Use for PowerMax performance questions, reports, or top-talker analysis.
when_to_use: Trigger phrases - "PowerMax response time last 24h", "top storage groups by IOPS", "FA port utilization", "is the array busy", "SRDF link throughput", "performance report for SG X"
---
# PowerMax performance

1. Pick the object and the window. Start with `get_performance_overview` (array) or the storage group.
   Use `list_performance_metrics` / `list_performance_keys` to get exact metric and key names; never guess
   metric names.
2. Retention: recent data is fine-grained, older data only at coarser (hourly / daily) granularity. If
   the tool says the range is unavailable, retry with the coarser granularity and say so.
3. Key metrics:
   - storage group: response time (read / write / overall), host IOPS, host MB/s, I/O size, read %
   - FE director / port: % busy, IOPS, MB/s, queue depth
   - array: overall response time, cache hit %, write-pending
   - SRDF: R1 write response time, link throughput, cycle time (async)
4. Report **avg and max** with the time of the max; for "who is causing it" rank storage groups by
   IOPS and MB/s at the peak time.
5. Correlate: alerts (`get_alerts`) and changes (`what_changed`) in the same window; SRDF health.
6. For unexplained behaviour, search the docs MCP (vendor `dell`, product `powermax` for the guides and
   the Events and Alerts guide, product `kb` for Dell KB articles) with the exact metric / alert text and
   the PowerMaxOS version.

Output: answer first, then a table (object | metric | avg | max | time of max | assessment), top
talkers, related alerts/changes, sources.
