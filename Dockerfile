FROM odoo:19.0
ENV ODOO_RC /etc/odoo/odoo.conf
COPY ./odoo.conf /etc/odoo/odoo.conf
