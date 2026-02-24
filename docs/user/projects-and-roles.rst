Projects and roles
==================

Core concepts
-------------

- A *project* is the container for your OKRs. It has a name, a deadline and a completion flag (done). Projects can also be archived.
- An *objective* describes what you want to achieve. Objectives can have child objectives (a hierarchy).
- A *key result* is a measurable outcome with start, current and end value.
- A *task* is a concrete action item belonging to a key result.

Roles in a project
------------------

Each user has a role per project:

- **Member**: participates in the project and can work on objectives, key results, and tasks inside the project scope.
- **Team lead (leader)**: has all member capabilities and can additionally manage the project itself (e.g., update or delete the project) and manage project members.

Administrators are special: they can perform project-lead actions regardless of role.

Role capabilities (overview)
----------------------------

.. list-table::
   :header-rows: 1

   * - Action
     - Member
     - Team lead
   * - View project content
     - Yes
     - Yes
   * - Create/update/delete objectives linked to the project
     - Yes
     - Yes
   * - Create/update/delete key results (within permitted objectives)
     - Yes
     - Yes
   * - Create/update/delete tasks (within permitted key results)
     - Yes
     - Yes
   * - Update/delete the project (name/deadline/done/icon)
     - No
     - Yes
   * - Add users to the project and assign roles
     - No
     - Yes

Project membership management
-----------------------------

Team leads can add users to a project and choose their project role (member or leader).
Use the project members screen in the UI to:

- list current members
- add a user
- assign the role (member/leader)
- remove a user from the project

Note: The project creator is automatically assigned the team lead role for that project.