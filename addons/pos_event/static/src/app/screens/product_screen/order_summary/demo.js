import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";

patch(OrderSummary.prototype, {
    async onOrderlineLongPress(ev, orderline) {
        if (!orderline.event_ticket_id) {
            return super.onOrderlineLongPress(ev, orderline);
        }
        const event = orderline.event_ticket_id.event_id;
        const registrationJson = {};
        orderline.event_registration_ids.forEach((registration, index) => {
            const answers = {};
            registration.registration_answer_ids.forEach((answer) => {
                answers[answer.question_id.id] =
                    answer.value_text_box ?? answer.value_answer_id?.id;
            });
            registrationJson[index] = answers;
        });

        const result = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            event,
            data: [
                {
                    product_id: orderline.product_id,
                    qty: orderline.qty,
                    ticket_id: orderline.event_ticket_id,
                    registration_ids: registrationJson,
                },
            ],
        });

        if (result) {
            this._processEventRegistrationResult(result, orderline);
        }
    },

    _processEventRegistrationResult(result, orderline) {
        for (const registrations of Object.values(result.byRegistration)) {
            for (const [regIdx, answers] of Object.entries(registrations)) {
                const originalReg = orderline.event_registration_ids[regIdx];
                if (!originalReg || typeof answers !== "object") {
                    continue;
                }
                const userData = {
                    name: originalReg.name,
                    email: originalReg.email,
                    phone: originalReg.phone,
                    company_name: originalReg.company_name,
                };
                for (const [questionId, answer] of Object.entries(answers)) {
                    const question = this.getQuestion(questionId);
                    if (!question) {
                        continue;
                    }
                    this.updateRegistrationAnswer(question, answer, originalReg, userData);
                }
                originalReg.update(userData);
            }
        }

        for (const [questionId, answer] of Object.entries(result.byOrder)) {
            const question = this.getQuestion(questionId);
            if (!question) {
                continue;
            }
            for (const originalReg of orderline.event_registration_ids) {
                const userData = {
                    name: originalReg.name,
                    email: originalReg.email,
                    phone: originalReg.phone,
                    company_name: originalReg.company_name,
                };
                if (!originalReg) {
                    continue;
                }
                this.updateRegistrationAnswer(question, answer, originalReg, userData);
                originalReg.update(userData);
            }
        }
    },

    getQuestion(questionId) {
        return this.pos.models["event.question"].get(parseInt(questionId));
    },

    updateRegistrationAnswer(question, answer, originalReg, userData) {
        const { question_type } = question;

        const existing = originalReg.registration_answer_ids.find(
            ({ question_id }) => question_id?.id === question.id
        );

        if (!answer) {
            if (existing) {
                existing.delete();
            }
            return;
        }
        const values = {
            question_id: question,
            registration_id: originalReg,
        };
        if (question_type === "simple_choice") {
            values.value_answer_id = { id: parseInt(answer) };
        } else {
            values.value_text_box = answer;

            if (["email", "phone", "name", "company_name"].includes(question_type)) {
                userData[question_type] = answer;
            }
        }
        if (existing) {
            existing.update(values);
        } else {
            this.pos.models["event.registration.answer"].create(values);
        }
    },
});
