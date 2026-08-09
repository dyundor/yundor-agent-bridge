# Yundor Agent Bridge v0.3 Implementation Task

## Role

You are the implementation engineer for Yundor Agent Bridge.

Your responsibility:

Upgrade the current bridge system into an autonomous AI engineering supervisor.

The system should allow:

User provides one ultimate goal.

The system automatically:

1. Analyze project state
2. Create development tasks
3. Send tasks to OpenCode
4. Monitor completion
5. Review results using GPT
6. Decide next action
7. Continue execution

---

# Important

Before coding, read:

- README.md
- existing configuration files
- current architecture
- all existing Python files

Do NOT rewrite the project.

Extend the current design.

---

# Target Architecture

User Goal

↓

Supervisor

↓

Planner

↓

Task Queue

↓

OpenCode Executor

↓

DeepSeek Coding

↓

Callback

↓

GPT Reviewer

↓

Memory Update

↓

Next Task

---

# Phase 1: Core Supervisor Framework

Create:

core/
supervisor.py
planner.py
reviewer.py
memory.py

---

# 1. Supervisor

File:
core/supervisor.py

Responsibilities:

- Manage autonomous loop
- Control task lifecycle
- Handle failures
- Trigger next task

Pseudo:

```python

while running:

    state = memory.load()

    task = planner.create_task(state)

    executor.run(task)

    result = wait_callback()

    review = reviewer.analyze(result)

    if review.approved:

        memory.update()

    else:

        create_fix_task()

2. Goal System
Create:
goals/
Example:
goals/market-intelligence.md
Format:

# Goal


Complete Yundor Market Intelligence system.


## Business Objective


Build a global bathroom market intelligence platform.

Capabilities:


- Market discovery

- Product opportunity analysis

- Buyer discovery

- Lead generation


## Constraints


- Control API cost

- Preserve architecture

- Require tests


3. Task Queue
Create:
queue/task_queue.json
Task format:

{

"id":"",

"project":"",

"objective":"",

"priority":"",

"constraints":[],

"success_criteria":[]

}

4. OpenCode Integration
Create:
opencode/

client.py

callback.py

executor.py

Responsibilities:
client:
send task to OpenCode
callback:
receive completion result
executor:
manage execution state
5. Callback API
Create endpoint:
POST /callback/task-complete
Example:

{

"task_id":"MI-15.69",

"status":"completed",

"files_changed":10,

"tests":"passed",

"commit":"xxxxx"

}

6. GPT Reviewer
Create:
core/reviewer.py

Reviewer must evaluate:

Did task achieve objective?

Does code introduce risks?

Are tests enough?

What is next task?
Return:

{

"approved":true,

"quality_score":90,

"issues":[],

"next_task":""

}

7. Memory System
Create:
memory/

PROJECT_STATE.md

TASK_HISTORY.md

FAILED_TASKS.md

DECISIONS.md

Purpose:
Prevent:
repeated mistakes

forgotten decisions

architecture drift

8. Configuration
Update:
config.yaml

Support:

supervisor:

 enabled:true

 max_iterations:100


gpt:

 model:"gpt-5.5-mini"


opencode:

 url:"http://127.0.0.1:4097"


Safety Rules
The system MUST NOT:
delete production data

purchase APIs

modify credentials

push to production automatically

The system MAY:
modify source code

run tests

create commits

update documentation

Testing Requirement
Before completion:
Run:
pytest

or existing test command.
Provide:
Implementation Summary
Files Changed
Test Result
Known Limitations
Next Recommendation
First Goal After Implementation
Load:
goals/market-intelligence.md

Prepare:
Sprint 15.69
Product → Qualified Buyer Pipeline
Do not implement Sprint 15.69 yet.
Only prepare the autonomous framework first.

---
```
