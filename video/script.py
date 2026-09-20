"""Guion del vídeo tutorial (inglés).

Cada escena tiene su locución y la especificación de lo que se ve. Las
duraciones salen del audio real, no de aquí.
"""

REPO = "github.com/Stevenkingx/DavinciResolve-Installer"

SCENES = [
    dict(
        id="01_hook", visual="terminal_error", headline="",
        text="If you have ever tried to install DaVinci Resolve on Linux, "
             "there is a good chance you have seen this. The installer stops, "
             "tells you a package called zlib is missing, and cancels. "
             "That is all you get.",
    ),
    dict(
        id="02_why", visual="terminal_error_annotated",
        headline="The package is not actually missing",
        text="But the package is not missing. Resolve's installer looks for a "
             "name that modern distributions no longer use. On Fedora it is "
             "called zlib-ng-compat. The check is simply wrong, and it stops "
             "the installation before it even starts.",
    ),
    dict(
        id="03_three", visual="three_problems",
        headline="Three things stand between you and a working Resolve",
        text="Get past that, and two more problems are waiting. Your graphics "
             "card needs the right compute runtime, and it is a different one "
             "for AMD and for NVIDIA. And Resolve ships its own old copies of "
             "three system libraries that make it quit when you export, or "
             "when you open a file dialog.",
    ),
    dict(
        id="04_meet", visual="app_home", headline="DaVinci Resolve Manager",
        text="This app handles all three. It is small, free and open source. "
             "You drag the zip file you downloaded from Blackmagic onto the "
             "window, and it takes care of the rest.",
    ),
    dict(
        id="05_install", visual="terminal_install",
        headline="Installing it takes three commands",
        text="Getting it is three commands. Clone the repository, run install "
             "dot s h, and it adds itself to your applications menu. No root "
             "needed here: everything goes into your home folder.",
    ),
    dict(
        id="06_scan", visual="zoom_cards",
        headline="First, it reads your system",
        text="When it opens, it checks your machine. Your distribution, your "
             "graphics card, whether the driver is actually responding, and "
             "which OpenCL platforms are active. If something here is wrong, "
             "Resolve will not run, and you find out before you install "
             "anything.",
    ),
    dict(
        id="07_edition", visual="zoom_edition",
        headline="Free or Studio",
        text="Then you pick your edition. Free and Studio are two different "
             "downloads. Studio needs an activation key or a USB dongle: "
             "without a licence it will install, but it will not start. The "
             "app links you to the right file, and warns you if you drop the "
             "other one.",
    ),
    dict(
        id="08_drop", visual="drop_animation",
        headline="Drag the zip onto the window",
        text="Now drag the zip onto the window. Do not unzip it first.",
    ),
    dict(
        id="09_plan", visual="app_plan",
        headline="It tells you what it will do, before doing it",
        text="Before touching anything, it shows you the whole plan. Here it "
             "will unpack the installer, run it with that broken package check "
             "disabled, set aside the conflicting libraries, and fix the "
             "folder ownership. Every step explains why it is there. The "
             "optional ones you can simply untick.",
    ),
    dict(
        id="10_run", visual="app_run",
        headline="One password, then it works through the list",
        text="Press start and enter your password once. Everything that needs "
             "permission is sent in a single batch, so you are never asked "
             "again. If you want to watch, the technical details drawer shows "
             "the full output of every command as it runs.",
    ),
    dict(
        id="11_done", visual="app_done",
        headline="Installed, patched and ready",
        text="When it finishes, Resolve is installed, patched and ready to "
             "open. Your projects and your database were never touched. They "
             "live in your home folder, not in opt.",
    ),
    dict(
        id="12_repair", visual="app_repair",
        headline="Already installed and misbehaving?",
        text="If Resolve is already installed and misbehaving, check and "
             "repair applies the fixes on their own. Starts and closes "
             "instantly with no message? That is folder ownership. Quits when "
             "you export? That is the libraries. It ticks only the ones your "
             "machine actually needs.",
    ),
    dict(
        id="13_outro", visual="outro", headline="",
        text="It is tested on Fedora, and it covers Debian, Ubuntu, Arch and "
             "openSUSE as well. Free and open source. You will find it at the "
             "link on screen.",
    ),
]
