# Retention and travel corrections

Integrates shared route selection/scoped route locking and actual shorter flee candidates. Completes bot out-of-range visibility cleanup before skipping client notification, removes missing-object forward references, and bounds diagnostic removed-object history to 4096 unique entries per map. TBC/Wrath also clean orphan reverse visibility GUIDs; Classic uses its native visibility implementation.

Preserves existing Arch4 object-delivery timing. The old review branches' extra VISIBILITY_SUMMARY and SLOW_OBJECT_SEND instrumentation are not included; no extra logging is introduced. Existing reviewed visibility notes describe the original branch, not this adapted release. No database/config changes. Actual-body regressions cover visibility exceptions and bounded history, plus shared travel and flee tests. Live memory savings are not established by these tests.

Missing-object diagnostic output remains human-only, preventing bot reconciliation from introducing synchronous custom-log traffic.
