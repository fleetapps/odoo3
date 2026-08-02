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
RUN test -f /opt/custom_addons/shopify_bisync/__manifest__.py \
    || (echo "ERROR: custom_addons/ is empty - git submodule not initialised" && exit 1)
