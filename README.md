![Red-Sandwich Harness architecture artwork](https://github.com/jjangkjy5607-dev/red-sandwich-harness/releases/download/v0.1.0/red-sandwich-banner.png)

# Red-Sandwich Harness (TSH-Auditor)

**Adversarial Gemini Red-Team Auditing & Deterministic TDD Sandwich Framework**

**Creator / Original Author:** Taejin Eom (TurboWork) · 엄태진

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#mit-license)
[![Public Spec](https://img.shields.io/badge/Scope-Public_Spec-455a64.svg)](#public-scope)

## Why an auditor belongs in the harness

AI-generated code can satisfy a happy-path example while missing boundary cases,
drifting from the agreed specification, or leaking validation information into training.
Red-Sandwich Harness adds an adversarial reviewer to a three-layer execution contract.

The defining mechanism is an **audit-to-test acceptance loop**: an independent
reviewer proposes concrete counterexamples, the implementer reproduces them locally,
and executable gates decide whether the revised implementation may proceed.
The architecture is defined by these responsibilities and contracts rather than
by the order in which reasoning models are switched.

## The four pillars

### 1. The Auditor — Gemini Red-Team

After code generation, Gemini's proposed role is to challenge the implementation
with missing values, extreme inputs, shape mismatches, and possible leakage paths.
Each finding should include a concrete failing input and the expected behavior.
Reproduce findings locally before accepting them. If a finding changes the agreed
contract, approve and record the specification change before locking new tests.
Then revise the implementation and rerun the relevant regression checks.

The public example uses a clearly named **offline mock**, not a Gemini integration.
Its fixed finite-value and magnitude checks illustrate an audit verdict;
they do not inspect source semantics or discover every leakage path.
Only an explicit Boolean `True` admits the next stage. `False`, `None`, strings,
and integers are rejected before contract checks and model fitting.

### 2. Top Bread — Spec-Lock TDD Gate

Define input/output contracts before implementation and block execution on failure.
The example requires a five-row DataFrame with exactly `x` and `y` columns,
zero missing/non-finite values, and correctly shaped, finite predictions.
`ValueError` gates remain active with Python's `-O` optimization flag.
This two-file release demonstrates the gate; a complete CI/TDD suite is outside its scope.

### 3. Core Filling — AST Pure Units

Enforce **35 physical lines per function** and **200 lines per source file**.
The example checks its own AST before fitting. `features` returns a copy of `x`
without changing the input; the orchestrator owns stateful model fitting.
Small units keep review context bounded. AST length checks and a model's review
do not prove functional purity or guarantee hallucination-free code.

### 4. Bottom Bread — Strict K-Fold Isolation

Each fold constructs a fresh `StandardScaler` + `LinearRegression` pipeline.
Only training rows reach `fit`; held-out rows use that fold's fitted preprocessing
through `predict`. No fitted scaler or model is reused across folds.
Freeze audit-derived contracts before evaluation; the example's magnitude bound
is fixed in advance and is not estimated from held-out data.
This isolates the demonstrated preprocessing fit. Group, temporal, target, and
adaptive-validation leakage still need checks suited to the actual application.

## Minimal proof of concept

[`example_red_sandwich.py`](example_red_sandwich.py) uses five synthetic rows,
`x = 0..4` and `y = 2x + 1`, created entirely in memory. The execution order is:

**AST preflight → mock audit verdict → input contract → pure feature extraction
→ five independent folds → prediction contract → fold MSE output.**

The example is under 50 lines. Its tiny linear dataset illustrates control flow,
not competition performance. No API key or Gemini network call is required.
"Deterministic" describes explicit checks and fixed demo inputs, not deterministic
LLM behavior or bit-for-bit identical numerical results on every platform.

Tested runtime: Python 3.13, NumPy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1.
With [uv](https://docs.astral.sh/uv/) installed, run this in PowerShell:

```powershell
Set-Location -LiteralPath 'D:\CodexProjects\red-sandwich-harness-public'
$env:UV_CACHE_DIR = 'D:\CodexProjects\.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = 'D:\CodexProjects\.runtime\python'
$env:TEMP = 'D:\CodexProjects\.tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
uv venv --python 3.13 'D:\CodexProjects\.runtime\red-sandwich-public'
uv pip install --python 'D:\CodexProjects\.runtime\red-sandwich-public\Scripts\python.exe' numpy==2.5.4 pandas==3.1.0 scikit-learn==1.9.1
& 'D:\CodexProjects\.runtime\red-sandwich-public\Scripts\python.exe' -B '.\example_red_sandwich.py'
```

## Public scope

The Git tree contains exactly this specification and the synthetic example.
The header illustration is hosted separately as a GitHub release attachment.
Production code, competition datasets, model weights, private feature logic, and
paid product files are excluded from this repository and its MIT grant.

## 한국어 요약

Red-Sandwich Harness(TSH-Auditor)는 엄태진(Taejin Eom / TurboWork)의 공개 아키텍처입니다.
Gemini가 실패 사례를 제안하는 적대적 감사 역할을 맡고, 로컬 재현과 합의된 회귀 테스트로
검토 결과를 구현 계약에 연결합니다. 모델 교체 순서보다 감사·재현·통과 조건에 초점을 둡니다.
입출력·결측 검증, 함수35줄·파일200줄 AST 제한, Fold별 독립 학습이 실행을 통제합니다.
공개 코드는 실제 Gemini 호출 대신 모의 감사 함수를 사용하며, 실전 데이터나 엔진은 포함하지 않습니다.
감사·길이 제한만으로 모든 환각과 누수의 제거를 보장하지 않고 각 게이트의 검증 범위를 명시합니다.

## MIT License

Copyright (c) 2026 Taejin Eom / TurboWork

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Get the Sandwich Workflow Kit on Gumroad

Apply a structured plan → build → review workflow with the **Sandwich Workflow Kit v2.7**:
editable English and Korean instructions, a Windows quickstart, FAQs, and two
15-step project blueprints, delivered as Markdown documents and supporting assets in a ZIP.

Starter covers personal noncommercial learning, Pro covers one person's commercial
or client work, and Team covers up to five named users in one organization.
Paid downloads follow their own product license, separate from this public MIT release.

**[👉 Get the Sandwich Workflow Kit v2.7 on Gumroad](https://turboworkai.gumroad.com/l/sandwich-workflow-kit)**

한국어: 실제 판매 상품인 v2.7 한영 문서 키트의 구성과 이용권은 위 링크에서 확인할 수 있습니다.
