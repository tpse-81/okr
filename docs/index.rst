OKR-Tool documentation
======================

.. figure:: ./icon.svg
   :scale: 30 %
   :align: left

What is this and how can I use it?
----------------------------------
OKR tools are designed to structure goals, measure progress, and improve transparency across projects. 

:ref:`feature-overview` gives a short overview of the functionalities supported by this **OKR-Tool**.

.. _feature-overview:

.. table:: Feature overview (excerpt) 
   :widths: auto

   =============================   =============================================
   Concept                         Supported functionalities
   =============================   =============================================
   OKR base features               Projects, Objectives, Key Results, ...
   Authentication                  TOTP, Webauthn
   Dashboard                       Upcoming Deadlines, Open Tasks, ...
   User Roles                      Admin, Teamlead, Member
   Internationalization            Supported languages: German, English
   Deployment                      Docker, Manual (Python & NodeJS)
   =============================   =============================================

How do I get started?
---------------------

If you want to host your own instance of the OKR tool, please follow the instructions at :doc:`./admin/index`.

If you're a user and want to learn how to use the app as efficiently as possible, please continue reading at :doc:`./user/index`.

Extending this documentation
----------------------------
This documentation uses ``reStructuredText`` syntax. See the
`reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
documentation for details.

To build this documentation, run ``sphinx-build docs _build`` in the project root directory.

To get a live preview while editing, run ``sphinx-autobuild docs _build/html``.


.. toctree::
   :numbered:
   :maxdepth: 5
   :caption: Contents:

   admin/index
   Python source code documentation <api/modules>
