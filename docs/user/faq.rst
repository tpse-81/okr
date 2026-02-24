FAQ
===

I get a “no permissions” / 403 error. Why?
-----------------------------------------

Most permission issues come from one of these cases:

- You are not a member of the project that contains the objective / key result / task.
- You are a member, but you are trying to modify the project itself (project settings), which requires the team lead role.

My key result update fails with “current value is out of bounds”.
---------------------------------------------------------------

The OKR tool enforces that the current value stays between start and end value (inclusive).
Example:

- start = 10
- end = 20
- allowed current range: 10..20

If you need to go beyond, adjust the end value first.

Why is an objective suddenly archived?
--------------------------------------

Objectives can be archived automatically when they are not linked to any active project.
This can happen after project deletion or after unlinking an objective from a project.

Where can I find the API?
-------------------------

If your instance exposes the OpenAPI UI, it is usually available at ``/docs``.