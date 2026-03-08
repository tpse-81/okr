Projects and roles
==================

Core concepts
-------------

The OKR tool uses four main building blocks:

- A **project** is the container for your OKRs. It has a name, a deadline, and a completion state.
- An **objective** describes what you want to achieve.
- A **key result** is a measurable outcome with start, current, and end value.
- A **task** is a concrete action item that belongs to a key result.

Roles in a project
------------------

Permissions are assigned per project.
This means that the same user can be a team lead in one project and a regular member in another.

There are two normal project roles:

- **Member**: works on objectives, key results, and tasks within the project scope
- **Team lead (leader)**: has all member permissions and can additionally manage the project itself and its members

Administrators are a special case.
They can usually perform project-lead actions regardless of their explicit project role.

What members can do
-------------------

As a member, you can usually:

- view the project and its content
- create, update, and delete objectives within the permitted project scope
- create, update, and delete key results within permitted objectives
- create, update, and delete tasks within permitted key results
- update day-to-day work inside the project

What team leads can do
----------------------

As a team lead, you can do everything a member can do.
In addition, you can usually:

- update the project itself
- delete the project
- change project-level settings such as name, deadline, done state, or icon
- add users to the project
- remove users from the project
- assign the project role of a member

Role overview
-------------

.. list-table::
   :header-rows: 1

   * - Action
     - Member
     - Team lead
   * - View project content
     - Yes
     - Yes
   * - Create, update, or delete objectives in the project scope
     - Yes
     - Yes
   * - Create, update, or delete key results in the project scope
     - Yes
     - Yes
   * - Create, update, or delete tasks in the project scope
     - Yes
     - Yes
   * - Update or delete the project itself
     - No
     - Yes
   * - Add or remove project members
     - No
     - Yes
   * - Assign project roles
     - No
     - Yes

Managing project membership
---------------------------

Project membership is usually handled by a team lead.
Typical actions on the project-members page are:

- list current members
- add a user to the project
- assign the role **member** or **leader**
- remove a user from the project

In many setups, the project creator is automatically assigned the team-lead role for that project.
