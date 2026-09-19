document.addEventListener("DOMContentLoaded", () => {
	const patientSelect = document.querySelector("[data-prescription-patient]");
	const appointmentSelect = document.querySelector("[data-prescription-appointment]");
	const appointmentHelp = document.querySelector("[data-prescription-appointment-help]");
	const visitSummary = document.querySelector("[data-visit-summary]");
	const visitTitle = document.querySelector("[data-visit-title]");
	const visitDescription = document.querySelector("[data-visit-description]");

	const updateVisitSummary = () => {
		const option = appointmentSelect?.selectedOptions[0];
		if (!option?.dataset.patientId || !visitSummary || !visitTitle || !visitDescription) {
			if (visitSummary) visitSummary.hidden = true;
			return;
		}
		visitTitle.textContent = `${option.dataset.date} at ${option.dataset.time} with ${option.dataset.doctor}`;
		visitDescription.textContent = option.dataset.reason;
		visitSummary.hidden = false;
	};

	if (patientSelect && appointmentSelect && appointmentHelp) {
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
			if (!selectedOption?.dataset.patientId || selectedOption.dataset.patientId !== patientId) {
				appointmentSelect.value = "";
			}
			appointmentSelect.disabled = !patientId || availableCount === 0;
			appointmentHelp.textContent = !patientId
				? "Select a patient to see completed visits."
				: availableCount
					? "Choose the completed visit for this prescription."
					: "This patient has no completed visits awaiting a prescription.";
			updateVisitSummary();
		};

		patientSelect.addEventListener("change", updateAppointments);
		appointmentSelect.addEventListener("change", updateVisitSummary);
		updateAppointments();
	}

	const list = document.querySelector("[data-medicine-list]");
	const addButton = document.querySelector("[data-add-medicine]");
	if (!list || !addButton) return;

	const updateRemoveControls = () => {
		const rows = list.querySelectorAll("[data-medicine-row]");
		rows.forEach((row) => {
			const button = row.querySelector(".remove-medicine");
			if (!button) return;
			button.hidden = rows.length === 1;
			button.disabled = rows.length === 1;
		});
	};

	list.addEventListener("click", (event) => {
		const button = event.target.closest(".remove-medicine");
		if (!button) return;
		const row = button.closest("[data-medicine-row]");
		if (row && list.querySelectorAll("[data-medicine-row]").length > 1) {
			row.remove();
			updateRemoveControls();
		}
	});

	addButton.addEventListener("click", () => {
		const template = list.querySelector("[data-medicine-row]");
		if (!template) return;
		const row = template.cloneNode(true);
		row.querySelectorAll("input").forEach((input) => {
			input.value = "";
		});
		list.appendChild(row);
		updateRemoveControls();
		row.querySelector("input[name='medicine']")?.focus();
	});

	updateRemoveControls();
});
