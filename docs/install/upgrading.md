#### Upgrading from Amniotic 0.x and fixing entity IDs

If you upgraded from the old version and need to fix entity IDs:

- Go into Devices and find both old and new Amniotic devices.
- Delete both (MQTT Info -> Delete)
- Restart the Add-On/Container, and just the new one should recreate itself.
- If you end up with funky Entity IDs (like
  `select.amniotic_theme_2`) click in the :recycle: button in the Entity ID box.
