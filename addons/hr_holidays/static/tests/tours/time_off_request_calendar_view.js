import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_request_calendar_view", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the first Thursday of the year",
<<<<<<< f5f29240f10f76dce15e34e2617ae4542cb0564c
            trigger: ".fc-daygrid-day.fc-day-thu",
            run: () => {
                const el = document.querySelector(
                    ".fc-daygrid-day.fc-day-thu:not(.fc-day-disabled)"
                ).firstChild;
                el.scrollIntoView();

                const fromPosition = el.getBoundingClientRect();
                fromPosition.x += el.offsetWidth / 2;
                fromPosition.y += el.offsetHeight / 2;

                el.dispatchEvent(
                    new MouseEvent("mousedown", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
                el.dispatchEvent(
                    new MouseEvent("mouseup", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
            },
||||||| d2799f147923e2a028aeb2a12c409e104cc7eddc
            trigger: ".fc-daygrid-day.fc-day-thu",
            run: () => {
                const el = document.querySelector(".fc-daygrid-day.fc-day-thu:not(.fc-day-disabled)").firstChild;
                el.scrollIntoView();

                const fromPosition = el.getBoundingClientRect();
                fromPosition.x += el.offsetWidth / 2;
                fromPosition.y += el.offsetHeight / 2;

                el.dispatchEvent(
                    new MouseEvent("mousedown", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
                el.dispatchEvent(
                    new MouseEvent("mouseup", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
            },
=======
            trigger: ".fc-daygrid-day.fc-day-thu:not(.fc-day-disabled)",
            run: "click",
>>>>>>> f18fd67c25aa22c82b96d6fe069a41bcac8bc50a
        },
        {
            content: "Save the leave",
            trigger: '.o_form_button_save',
            run: "click",
        },
    ],
});
