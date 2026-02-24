function formatNumber(amount) {
    return new Intl.NumberFormat("ru-RU").format(amount);
}

document.addEventListener("DOMContentLoaded", () => {
    const forms = document.querySelectorAll(".payment-form");

    forms.forEach((form) => {
        const hourlyRate = Number(form.dataset.pricePerHour || 500);
        const daysInput = form.querySelector('input[name="days"]');
        const hoursInput = form.querySelector('input[name="hours"]');
        const totalHoursNode = form.querySelector("[data-total-hours]");
        const totalPriceNode = form.querySelector("[data-total-price]");

        const refresh = () => {
            const days = Math.max(0, Number(daysInput.value) || 0);
            const hours = Math.max(0, Number(hoursInput.value) || 0);
            const totalHours = Math.max(1, days * 24 + hours);
            const totalPrice = totalHours * hourlyRate;

            totalHoursNode.textContent = String(totalHours);
            totalPriceNode.textContent = formatNumber(totalPrice);
        };

        daysInput.addEventListener("input", refresh);
        hoursInput.addEventListener("input", refresh);
        refresh();
    });
});
