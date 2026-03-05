import { test, expect, describe, beforeEach } from "@odoo/hoot";
import { createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import { MockServer, onRpc } from "@web/../tests/web_test_helpers";

definePosSelfModels();

beforeEach(async () => {
    const mockCreateBancontactPayment = async (request) => {
        const { params } = await request.json();
        const { order_id, payment_id } = params;
        const order = MockServer.env["pos.order"].browse(order_id)[0];
        const configId = order.config_id;

        const payment = MockServer.env["pos.payment"].browse(payment_id)[0];
        if (payment.amount < 0) {
            throw new Error("Invalid payment amount");
        }
        payment.bancontact_id = "bancontact_" + payment.id;
        payment.qr_code = `https://example.com/qrcode/${payment.bancontact_id}`;

        const paymentFields = MockServer.env["pos.payment"]._load_pos_data_fields(configId);
        const orderFields = MockServer.env["pos.order"]._load_pos_data_fields(configId);
        return {
            "pos.order": MockServer.env["pos.order"].read([order.id], orderFields, false),
            "pos.payment": MockServer.env["pos.payment"].read([payment.id], paymentFields, false),
        };
    };

    onRpc("/pos-self-order/create-bancontact-pay-payment", mockCreateBancontactPayment);
});

describe("sendPaymentRequest", () => {
    test("failed to create bancontact payment", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const opts = { amount: -1, payment_status: "waiting" }; // Invalid amount to trigger failure
        const paymentline = createPaymentLine(store, order, display, opts);

        let failed = false;
        try {
            await paymentline.payment_interface.sendPaymentRequest(paymentline);
        } catch {
            failed = true;
        }

        expect(failed).toBe(true);
        expect(paymentline.bancontact_id).toBeEmpty();
        expect(paymentline.qr_code).toBeEmpty();
        expect(paymentline.payment_status).toBe("waiting");
    });

    test("success to create bancontact payment", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const opts = { payment_status: "waiting" };
        const paymentline = createPaymentLine(store, order, display, opts);

        const result = await paymentline.payment_interface.sendPaymentRequest(paymentline);
        const bancontactId = "bancontact_" + paymentline.id;
        const qrCodeUrl = `https://example.com/qrcode/${bancontactId}`;

        expect(result).toBe(true);
        expect(paymentline.bancontact_id).toBe(bancontactId);
        expect(paymentline.qr_code).toBe(qrCodeUrl);
        expect(paymentline.payment_status).toBe("waiting");
    });
});
