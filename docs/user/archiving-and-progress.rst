Archiving and progress
======================

This page explains two things that often confuse users:

- how progress is calculated
- why content may disappear from the active view

Progress calculation
--------------------

Progress is derived from key results.

- **Key-result progress** is based on the distance from start value to current value,
  relative to the distance from start value to end value.
- If the start value and end value are equal, the key result is treated as fully done.
- **Objective progress** is the average progress of its key results.
- If an objective has no key results, it is treated as fully done.

Project progress shown on the dashboard is usually derived from the objectives linked to that project.

Practical meaning
-----------------

This means:

- tasks help you organize the work
- key-result values determine measurable progress
- objective progress depends on the underlying key results

If a project looks incomplete even though many tasks are done, check whether the key-result values were updated as well.

Archiving behaviour
-------------------

Projects and objectives can be archived.
Archived items may disappear from the normal active view.

Objectives are automatically archived if they are no longer linked to any active
(not archived) project.
Objective hierarchies are respected: if a parent objective is still active,
its child objectives stay active as well.

This matters especially when:

- a project is deleted
- an objective is removed from a project
- objectives are moved inside a hierarchy

What to check if something disappears
-------------------------------------

If an objective is suddenly missing from the active view:

1. Check whether it was archived.
2. Check whether it is still linked to an active project.
3. Check whether a parent objective or project was archived or removed.

If you link the objective to an active project again, it should normally become active again.
