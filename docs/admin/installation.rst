Installation
------------
There are two ways of setting up the app:

- via Docker Compose: see :ref:`docker-installation`
- manually (currently only supported for Linux): see :ref:`manual-installation`

.. _docker-installation:
Setup using Docker Compose
~~~~~~~~~~~~~~~~~~

.. attention:: This guide assumes that you have already installed and started `Docker <https://www.docker.com/>`_ and `Docker Compose <https://docs.docker.com/compose/>`_. If you don't, please follow their setup instructions first or use the :ref:`manual-installation` method.

Steps
"""""
1. Create a file called `docker-compose.yml` and copy the below contents into that file.
2. Modify the contents of `docker-compose.yml` for your needs. In most cases, you only have to change the following settings:
	- ``PUBLIC_API_URL``: replace this with the public URL to your backend (e.g. *okr-api.example.com*). If you're only running the app locally without exposing it publicly to the internet, you can skip this step.
	- ``ports``: For the frontend and the backend each, you can change the port it listens on. For example, if you want the backend to listen on port ``5000`` instead, change the value of ``ports`` in the backend section from `8000:8000` to ``5000:8000``.

.. literalinclude :: ../../docker-compose.yml
   :language: yaml
   :caption: ``docker-compose.yml``

3. Grab the example config from :doc:`configuration`, copy it into a file called ``config.toml`` and modify it to your needs. For more details, read the :doc:`configuration` documentation.

4. After you finished configuring the app, you can start it by executing the commands below

.. code-block:: sh

   docker compose pull
   docker compose up

5. Configure your reverse proxy to forward traffic to the app, see :ref:`reverse-proxy-setup`.

.. _manual-installation:
Manual installation
~~~~~~~~~~~~~~~~~~~

.. attention:: The guide assumes that you have Git, NodeJS and Python installed. Please make sure you have them installed before following the instructions.

Run the backend
"""""""""""""""

1. Download the app and all dependencies by executing the following commands:

.. code-block:: sh

   git clone https://github.com/tpse-81/okr.git
   python -m venv .venv
   source .venv/bin/activate
   pip install .

2. Next, grab the example config from :doc:`configuration`, copy it into a file called ``config.toml`` and modify it to your needs. For more details, read the :doc:`configuration` documentation.

3. Then, you can start the app by executing

.. code-block:: sh

   litestar run

The backend now listens on *http://localhost:8000*.

Run the frontend
""""""""""""""""
You can set up the frontend by executing the following commands:

.. code-block:: sh

   git clone https://github.com/tpse-81/okr-frontend.git
   npm install && npm build

   # if serving the app publicly to the internet, please make sure
   # to change this to the URL of the frontend, e.g. `https://okr-api.example.com`,
   # after you configured your reverse proxy
   PUBLIC_API_URL="http://localhost:8000" node build/index.js

The frontend now listens on *http://localhost:3000*.

Next steps
""""""""""
- This guide only explains how to get everything running, but by using this guide the changes will not persist after reboot, i.e. the app is not running anymore if you restart the server. You probably want to setup one Systemd service each for the frontend and the backend, as explained in `this guide <https://medium.com/@benmorel/creating-a-linux-service-with-systemd-611b5c8b91d6>`_.
- Configure your reverse proxy as explained in :ref:`reverse-proxy-setup`.

.. _reverse-proxy-setup:
Reverse proxy configuration
-------------------
.. hint:: This guide assumes that you own a web domain and already configured its nameservers to point to your server. If that's not the case yet, please do so first.

.. danger:: This guide doesn't cover setting up TLS, so by using this setup, all communication with the app over the internet is unencrypted. For example, you can follow `this guide <https://medium.com/@vinoji2005/guide-to-setup-lets-encrypt-ssl-in-nginx-be3d641bb58a>`_ to set up TLS with Nginx and Certbot.

Now, you can point your reverse proxy (e.g. `Nginx <https://nginx.org/en/docs/beginners_guide.html>`_) to forward traffic to your domain to the ports of the app. If you use an other reverse proxy, please consult its documentation instead.

An example config file for NGINX could look like

.. code-block:: nginx

   # forward all traffic from okr.example.org to the OKR frontend
   server {
     listen       80;
     server_name  okr.example.org;

     location / {
       proxy_pass http://localhost:3000;	
     }
   }

   # forward all traffic from okr-api.example.org to the OKR backend
   server {
     listen       80;
     server_name  okr-api.example.org;

     location / {
       proxy_pass http://localhost:8000;	
     }
   }

Make sure to restart NGINX after configuring it, e.g. by using ``systemctl restart nginx``.

Now you should be able to open the app with a browser by navigating to the domain you configured (e.g. ``http://okr.example.org``). After you confirmed that it works, please make sure to set up TLS as quickly as possible, so that you can reach the app at ``https://okr.example.org`` and all traffic is secure.
