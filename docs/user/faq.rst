FAQ
===

I get a “no permissions” or 403 error. Why?
------------------------------------------

Most permission problems come from one of these situations:

- You are not a member of the project that contains the objective, key result, or task.
- You are a project member, but you are trying to change the project itself, which usually requires the team-lead role.

Start by checking whether you are in the correct project and whether your role is sufficient for the action.

My key-result update fails with “current value is out of bounds”.
----------------------------------------------------------------

The OKR tool requires the current value to stay between the start value and the end value, inclusive.

Example:

- start = 10
- end = 20
- allowed current range = 10 to 20

If you need to go beyond that range, adjust the end value first.

Why is an objective suddenly archived?
--------------------------------------

Objectives can be archived automatically when they are no longer linked to any active project.
This can happen after a project deletion or after unlinking an objective from a project.

Check :doc:`archiving-and-progress` for details.

I finished tasks, but the progress still looks wrong.
-----------------------------------------------------

Tasks and measurable progress are not the same thing.
Task states help organize the work, but progress is derived from key-result values.
Make sure the current value of the relevant key result has also been updated.

Where can I change my password or security settings?
----------------------------------------------------

Open **⋯ (More)** → **Account**.
There you can usually change your password, manage TOTP, and register passkeys.

Where can I find the API?
-------------------------

If your instance exposes the OpenAPI UI, it is usually available at ``/docs``.
