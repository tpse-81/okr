Account and security
====================

This page covers password changes, two-factor authentication (2FA), and passkeys.
All of these actions are available from **⋯ (More)** → **Account**.

Changing your password
----------------------

To change your password:

1. Open **⋯ (More)** → **Account**.
2. Enter your current password.
3. Enter your new password.
4. Repeat the new password for confirmation.
5. Click **Change password**.

This allows you to update your password without administrator support.

.. figure:: _images/change_password.png
   :alt: Password change screen
   :width: 900px

Two-factor authentication (TOTP)
--------------------------------

Depending on how your instance is configured, you may be able to enable two-factor authentication using TOTP.
TOTP means that, in addition to your password, you confirm your login with a time-based code from an authenticator app.

Enable 2FA
~~~~~~~~~~

To enable 2FA:

1. Open **⋯ (More)** → **Account**.
2. Create a new token.
3. Add the shown secret to your authenticator app, either manually or by scanning the QR code.
4. Enter the generated code in the UI to confirm the setup.

.. figure:: _images/create2FA.png
   :alt: 2FA setup screen with secret key and QR code
   :width: 900px

Disable 2FA
~~~~~~~~~~~

To disable 2FA, enter a valid TOTP code in the deactivation field and confirm the action.

.. figure:: _images/disable2FA.png
   :alt: 2FA deactivation screen
   :width: 900px

Passkeys (WebAuthn)
-------------------

A passkey is a device-based login credential.
Depending on your setup, it can be used as an additional login factor.

To register a passkey:

1. Open **⋯ (More)** → **Account**.
2. In the **Passkeys (WebAuthn)** section, click **Register passkey**.
3. Follow the system dialog shown by your browser or operating system.

On Windows, this dialog is usually shown as **Windows Security**.
It may ask you to save a passkey for the current site and confirm the action with a PIN or another device method.

Once the flow completes, the passkey is stored on your device.

.. figure:: _images/registerPasskey.png
   :alt: Passkey registration button
   :width: 900px

TOTP vs. passkeys
-----------------

The two features are related but not identical:

- **TOTP** uses a code from an authenticator app.
- **Passkeys** use a credential stored on a device or in a browser ecosystem.

It is often useful to keep a backup option so that you do not lose access if one method becomes unavailable.

Password resets by an administrator
-----------------------------------

If an administrator resets your password, your existing 2FA setup may also be removed.
If that happens, log in again and configure your security settings once more.
