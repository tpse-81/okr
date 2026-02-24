Working with OKRs
=================

Typical workflow
----------------

1. **Create a project** (usually done by a team lead).
2. **Add project members** and assign roles.
3. **Create objectives** inside the project.
4. **Create key results** for each objective.
5. **Track progress** by updating the key result current value.
6. **Add tasks** under key results and update their state.
7. Mark the project as **done** once completed.

Objectives
----------

Objectives have:

- a name
- a description
- optional child objectives (hierarchy)

Key results
-----------

Key results are numeric and have:

- start value
- current value
- end value

When updating values, the current value must remain within the bounds of start and end value (inclusive), otherwise the update fails.

Tasks
-----

Tasks belong to a key result and have:

- description
- state

Available task states are:

- ``open``
- ``planned``
- ``in_progress``
- ``done``
- ``cancelled``

A good pattern is: define tasks when you create the key result, then keep the state up to date during the week.