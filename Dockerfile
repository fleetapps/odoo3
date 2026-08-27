FROM odoo:19.0
ENV ODOO_RC /etc/odoo/odoo.conf
COPY ./odoo.conf /etc/odoo/odoo.conf

# Custom addons come from the `custom_addons` git submodule, which tracks
# fleetapps/odoo-apps @ 19.0 — that repo stays the single source of truth, this
# one just pins a commit of it.
#
# Deliberately NOT copied to /var/lib/odoo/custom_addons or /mnt/extra-addons:
# the base image declares both as VOLUMEs, so a Render persistent Disk (or the
# anonymous volume Docker creates) mounted at either path can mask files baked
# in at build time, and the modules would silently vanish at runtime. /opt is
# plain image filesystem, so what we copy is what runs.
COPY --chown=odoo:odoo ./custom_addons /opt/custom_addons

# Fail the build loudly if the submodule was not checked out. Without this the
# COPY above happily produces an empty directory, the build goes green, and the
# only symptom is an Apps list with none of our modules in it.
#
# Checks for *any* module rather than one by name: the odoo-apps 19.0 branch is
# periodically trimmed to the App Store-ready set, and a guard naming a module
# that gets trimmed away fails every build for the wrong reason.
RUN ls /opt/custom_addons/*/__manifest__.py >/dev/null 2>&1 \
    || (echo "ERROR: custom_addons/ is empty - git submodule not initialised" && exit 1)

# Print what actually got baked in. This is the one line to read in the Render
# build log to answer "did this deploy pick up my push?" - the alternative is
# deploying, opening the app, and inferring the version from the UI.
RUN echo "custom_addons baked into this image:" \
 && for m in /opt/custom_addons/*/__manifest__.py; do \
        echo "  $(basename $(dirname "$m")) \
$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$m" | head -1)"; \
    done
