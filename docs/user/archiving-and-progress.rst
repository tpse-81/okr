Archiving and progress
======================

Progress calculation
--------------------

Progress is computed from key results:

- **Key result progress** is based on the distance from start to current, relative to the distance from start to end.
  If start and end are equal, the key result is treated as fully done.
- **Objective progress** is the average progress of its key results.
  If an objective has no key results, it is treated as fully done.

Project progress shown on the dashboard is typically derived from the objectives linked to the project.

Archiving behaviour
-------------------

Projects and objectives can be archived.

Objectives are automatically archived if they are no longer linked to any *active* (not archived) project.
Objective hierarchies are respected: if a parent objective is active, its child objectives stay active as well.

This matters especially when:

- a project is deleted
- an objective is removed from a project
- objectives are moved in a hierarchy

Practical advice:

- If an objective disappears from your active view, check whether it was archived.
- If you re-link an objective to an active project, it should become unarchived again.