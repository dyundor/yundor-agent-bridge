# Design Decisions

## Product Normalization
- Products are normalized from noisy shipment descriptions
- Categories: 浴室水龙头, 龙头配件与零件, 淋浴底盆, 浴缸, 淋浴房与淋浴门, 花洒与淋浴系统, 淋浴背板与墙板, 浴缸与淋浴排水件, 卫浴阀门

## Hot Products Scoring
- 12-month shipment count: 55%
- Buyer coverage: 30%
- Weight (log scale): 15%

## Data Sources
- Shipment data (import records)
- Company profiles with website verification
- CRM leads and contacts module

## Paid API Policy
- ImportYeti: 100 credit budget, min 25 reserve
- All paid calls go through gateway, never from UI
- Tests use mock/fixtures only

## 2026-08-09: OpenCode v1.18.15 session directory limitation

OpenCode server v1.18.15 `POST /session` accepts `{directory}` in request body
but ignores it. The session working directory is fixed to whichever directory
`opencode serve` was started from.

**Impact**: Bridge's `opencode_client.create_session(directory)` call passes
`directory` without error but has no effect. All sessions share the server's
CWD.

**Workaround**: Start `opencode serve` from the target project directory.
If the bridge needs to work across multiple projects, either:
1. Start one server per project on different ports
2. Wait for a future OpenCode release that honors the `directory` field

**Rationale**: This is a server-side behavior of opencode v1.18.15.
The bridge should document this limitation rather than work around it
with fragile process management.

## 2026-08-09: MI-TEST-001 Result

Status: error, Commit: 

**Rationale**: End-to-end test with real OpenCode executor

## 2026-08-09: MI-TEST-001

Status=timeout, Commit=fe42dbd7ff4f

**Rationale**: e2e test with real executor

## 2026-08-09: MI-TEST-002

Status=completed, Commit=b7e2d32d3bac, Approved=False

**Rationale**: e2e test #2

## 2026-08-09: MI-TEST-003 Final

Approved=False, Quality=0, GPT=fallback

**Rationale**: Phase 5.1 GPT reviewer verification

## 2026-08-09: MI-TEST-003

commit=29908a8ea918 approved=False L1=True

**Rationale**: Phase 5.1

## 2026-08-09: MI-PILOT-001

analysis completed, approved=False

**Rationale**: Architecture pilot

## 2026-08-09: MI-REVIEW-001

Approved=False, Quality=50, Technical=50, Business=50

**Rationale**: Real GPT reviewer activation test

## 2026-08-09: MI-15.70-A

Approved=True Q=85 T=85 B=85

**Rationale**: Phase 1: Product resource analysis

## 2026-08-09: MI-15.70-B retry

Approved=False

**Rationale**: Retry review

## 2026-08-09: MI-15.70-B final

Approved=False Q=85 T=80 B=90

**Rationale**: Phase 2: Expand representative products

## 2026-08-09: MI-15.70-B2

Approved=False Q=85 T=90 B=80

**Rationale**: Complete images + tests

## 2026-08-09: MI-15.71-A

Approved=False Q=88 T=90 B=85

**Rationale**: Data confidence model

## 2026-08-09: MI-15.71-B

Approved=False Q=85 T=85 B=85

**Rationale**: Confidence visualization

## 2026-08-09: MI-15.71-B2

Approved=False Q=88

**Rationale**: Confidence UX fixes

## 2026-08-09: MI-15.72-A

Approved=False Q=88 T=90 B=85

**Rationale**: TrendMetric data model

## 2026-08-09: MI-15.72-B

Approved=False Q=85 T=85 B=85

**Rationale**: Trend API endpoint

## 2026-08-09: MI-15.72-B2

Approved=False

**Rationale**: API fixes

## 2026-08-09: GPT-1

Action=execute Decision=retry Q=0 T=0 B=0 D=0

**Rationale**: GPT manager rationale: Sprint 15.70 (representative product resources) is not yet complete — the analysis phase (15.70-A) passed, but the implementation phase (15.70-B) failed multiple times. The current state shows 6 conse

## 2026-08-09: GPT-2

Action=execute Decision=skip Q=90 T=90 B=70 D=100

**Rationale**: GPT manager rationale: Sprint 15.70 implementation failed due to review API unavailability, not code issues. The analysis phase (15.70-A) passed with Q=85. The implementation task is well-defined and the failure was infrast

## 2026-08-09: GPT-3

Action=execute Decision=retry Q=40 T=45 B=20 D=30

**Rationale**: GPT manager rationale: Sprint 15.70 implementation (MI-15.70-B) failed due to review API unavailability, not code issues. The analysis phase passed and the task is well-defined. Retry the implementation with a smaller, safe

## 2026-08-09: GPT-1

Action=execute Decision=retry Q=20 T=15 B=10 D=50

**Rationale**: GPT manager rationale: Sprint 15.73-A (trend visualization) is marked completed in task history, but the changelog only shows bridge setup. The next planned sprint is 15.73-B which should focus on completing the trend visua

## 2026-08-09: GPT-1

Action=execute Decision=approve Q=85 T=88 B=80 D=95

**Rationale**: GPT manager rationale: Sprint 15.73-A (trend visualization) is marked completed in task history, but the changelog only shows bridge setup. The recent failure indicates the frontend chart component was never actually built.
