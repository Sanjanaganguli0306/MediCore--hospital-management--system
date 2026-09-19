document.addEventListener('DOMContentLoaded', () => {
	const form = document.querySelector('#appointment-form');
	if (!form) return;

	const doctor = form.querySelector('#doctor-select');
	const dateInput = form.querySelector('#appointment-date');
	const slotGrid = form.querySelector('#slot-grid');
	const reason = form.querySelector('#slot-reason');
	const timeInput = form.querySelector('#appointment-time');
	const patientSearch = form.querySelector('[name="patient_search"]');
	const patientId = form.querySelector('[name="patient_id"]');
	const options = [...form.querySelectorAll('#patient-options option')];
	const doctorDirectory = [...form.querySelectorAll('#doctor-directory [data-doctor-id]')];
	const patientSummary = form.querySelector('[data-patient-summary]');
	const doctorSummary = form.querySelector('[data-doctor-summary]');

	function updatePatientSummary(option) {
		if (!option || !patientSummary) {
			if (patientSummary) patientSummary.hidden = true;
			return;
		}
		patientSummary.querySelector('[data-patient-name]').textContent = option.dataset.name;
		patientSummary.querySelector('[data-patient-meta]').textContent = `${option.dataset.code} · Blood group: ${option.dataset.bloodGroup}`;
		patientSummary.querySelector('[data-patient-contact]').textContent = `${option.dataset.phone} · ${option.dataset.email}`;
		patientSummary.hidden = false;
	}

	function updateDoctorSummary() {
		const record = doctorDirectory.find((item) => item.dataset.doctorId === doctor.value);
		if (!record || !doctorSummary) {
			if (doctorSummary) doctorSummary.hidden = true;
			return;
		}
		doctorSummary.querySelector('[data-doctor-name]').textContent = record.dataset.name;
		doctorSummary.querySelector('[data-doctor-meta]').textContent = `${record.dataset.specialization} · ${record.dataset.qualification}`;
		doctorSummary.querySelector('[data-doctor-contact]').textContent = `${record.dataset.branch} · ${record.dataset.phone} · ${record.dataset.email}`;
		doctorSummary.hidden = false;
	}

	function renderSlots(payload) {
		slotGrid.replaceChildren();
		reason.textContent = payload.reason || '';
		if (!payload.slots.length) {
			slotGrid.innerHTML = '<p class="muted">No available slots.</p>';
			return;
		}
		payload.slots.forEach((slot) => {
			const button = document.createElement('button');
			button.type = 'button';
			button.className = 'slot-chip';
			button.textContent = slot.time;
			button.disabled = !slot.available;
			if (!slot.available) button.classList.add('is-unavailable');
			button.addEventListener('click', () => {
				slotGrid.querySelector('.slot-chip.is-selected')?.classList.remove('is-selected');
				button.classList.add('is-selected');
				timeInput.value = slot.time;
			});
			slotGrid.appendChild(button);
		});
	}

	async function loadSlots() {
		timeInput.value = '';
		if (!doctor.value || !dateInput.value) {
			slotGrid.innerHTML = '<p class="muted">Choose a doctor and date to load slots.</p>';
			reason.textContent = '';
			return;
		}
		slotGrid.innerHTML = '<p class="muted">Loading slots...</p>';
		const response = await fetch(`${form.dataset.slotsUrl}?doctor_id=${encodeURIComponent(doctor.value)}&date=${encodeURIComponent(dateInput.value)}`);
		renderSlots(await response.json());
	}

	doctor.addEventListener('change', () => {
		updateDoctorSummary();
		loadSlots();
	});
	dateInput.addEventListener('change', loadSlots);
	patientSearch.addEventListener('change', () => {
		const match = options.find((option) => option.value === patientSearch.value);
		patientId.value = match?.dataset.patientId || '';
		updatePatientSummary(match);
	});
	updatePatientSummary(options.find((option) => option.dataset.patientId === patientId.value));
	updateDoctorSummary();
	loadSlots();
});
