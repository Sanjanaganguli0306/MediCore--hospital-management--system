document.addEventListener("DOMContentLoaded", () => {
	const patientSelect = document.querySelector("[data-billing-patient]");
	const appointmentSelect = document.querySelector("[data-billing-appointment]");
	const appointmentHelp = document.querySelector("[data-billing-appointment-help]");
	const description = document.querySelector("#description");
	const unitPrice = document.querySelector("#unit-price");
	if (!patientSelect || !appointmentSelect || !appointmentHelp) return;

	const appointmentOptions = Array.from(appointmentSelect.options).slice(1);
	const updateAppointments = () => {
		const patientId = patientSelect.value;
		let availableCount = 0;
		appointmentOptions.forEach((option) => {
			const available = option.dataset.patientId === patientId;
			option.hidden = !available;
			option.disabled = !available;
			if (available) availableCount += 1;
		});

		const selectedOption = appointmentSelect.selectedOptions[0];
		if (selectedOption?.dataset.patientId && selectedOption.dataset.patientId !== patientId) {
			appointmentSelect.value = "";
		}
		appointmentSelect.disabled = !patientId || availableCount === 0;
		appointmentHelp.textContent = !patientId
			? "Select a patient to view completed visits that are ready for billing."
			: availableCount
				? "Choose a completed visit, or leave this as a general charge."
				: "This patient has no completed visits awaiting an invoice.";
	};

	appointmentSelect.addEventListener("change", () => {
		const option = appointmentSelect.selectedOptions[0];
		if (!option?.dataset.patientId) return;
		if (description && !description.value.trim()) description.value = option.dataset.description;
		if (unitPrice && !unitPrice.value.trim()) unitPrice.value = option.dataset.fee;
	});
	patientSelect.addEventListener("change", updateAppointments);
	updateAppointments();
});
