export const followInstructionsTerminalStep = () => ({
    content: "Check that the payment page shows the terminal instructions container",
    trigger: ".payment-state-container h1:contains('Follow instructions on the terminal')",
});
export const scanQrCodeStep = () => ({
    content: "Check that the payment page shows the QR code to pay",
    trigger: ".payment-state-container h1:contains('Scan the QR code to pay')",
});
export const processingPaymentStep = () => ({
    content: "Check that the payment page shows the processing payment message",
    trigger: ".payment-state-container h1:contains('Processing your payment...')",
});
export function notifiedDanger(message) {
    return {
        content: "close the notification",
        trigger: `.o_notification:has(.o_notification_bar.bg-danger):has(.o_notification_content:contains('${message}')) .o_notification_close`,
        run: "click",
    };
}
