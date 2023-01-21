Mitsuba Blender Addon
---------------------

Authors:
Wenzel Jakob, Francesc Juhé, Bartosz Styperek

This directory contains the addon for Blender -> Mitsuba Renderer
integration. It is based on the excellent LuxBlend 2.5 code from
Luxrender project.

It also uses a custom 'extensions_framework' taken from the original
'Blender 2.5 Extensions Framework' by Doug Hammond from Blender and
with some modifications also from Luxrender project.

Mitsuba Blender exporter tries to convert all Blender scene information
to Mitsuba Renderer format. Custom properties panels are added to
Blender UI to set Mitsuba Renderer options and custom attributes.


Installation Instructions:
--------------------------

Copy the 'mtsblend' folder into Blender scripts/addons directory and
then enable Mitsuba addon on 'Addons > Render' section of Blender
'User Preferences' panel.

After enabling the addon, configure the 'Path to Mitsuba Installation'
setting that appears under Mitsuba addon on the same 'User Preferences'
panel by selecting the folder where Mitsuba Renderer binary is installed.

Blender might have to be restarted after configuring 'Exectuable Path'
for Material preview to work.
