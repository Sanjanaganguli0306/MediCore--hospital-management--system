document.addEventListener('DOMContentLoaded', () => {
  const updateThemeControls = () => {
    const dark = document.documentElement.dataset.theme === 'dark';
    document.querySelectorAll('.theme-toggle').forEach((button) => {
      button.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
      button.setAttribute('aria-pressed', String(dark));
      button.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
    });
  };

  updateThemeControls();
  document.querySelectorAll('.theme-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      document.documentElement.classList.toggle('dark', next === 'dark');
      localStorage.setItem('medicore-theme', next);
      updateThemeControls();
    });
  });

  const menu = document.querySelector('.menu-toggle');
  if (menu) {
    menu.addEventListener('click', () => {
      const open = document.body.classList.toggle('nav-open');
      menu.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('.flash button').forEach((button) => {
    button.addEventListener('click', () => button.parentElement.remove());
  });
  window.setTimeout(() => document.querySelectorAll('.flash').forEach((flash) => flash.remove()), 5000);

  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.getAttribute('aria-controls'));
      if (!input) return;

      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      const label = `${visible ? 'Hide' : 'Show'} ${input.labels[0].textContent.toLowerCase()}`;
      button.setAttribute('aria-label', label);
      button.title = label;
    });
  });

  const roleSelect = document.querySelector('[data-role-select]');
  const roleHelp = document.querySelector('[data-role-help]');
  if (roleSelect && roleHelp) {
    const roleHelpText = {
      admin: 'Admins can manage the MediCore workspace, clinical records, billing, and staff access.',
      doctor: 'Doctors receive a linked clinician profile for appointments and prescriptions.',
      receptionist: 'Receptionists can manage patient records and appointments.',
    };
    const updateRoleHelp = () => {
      roleHelp.textContent = roleHelpText[roleSelect.value] || '';
    };
    roleSelect.addEventListener('change', updateRoleHelp);
    updateRoleHelp();
  }

  const doctorEditor = document.querySelector('.doctor-edit-form');
  if (doctorEditor) {
    const previewFields = {
      name: '[data-doctor-preview-name]',
      specialty: '[data-doctor-preview-specialty]',
      branch: '[data-doctor-preview-branch]',
      experience: '[data-doctor-preview-experience]',
      status: '[data-doctor-preview-status]',
    };
    const emptyValues = {
      name: 'New clinician',
      specialty: 'Specialization pending',
      branch: 'Branch pending',
      experience: 'Not recorded',
    };
    doctorEditor.querySelectorAll('[data-doctor-preview]').forEach((field) => {
      field.addEventListener('input', () => {
        const key = field.dataset.doctorPreview;
        const preview = document.querySelector(previewFields[key]);
        if (!preview) return;
        const value = field.value.trim();
        if (key === 'experience') {
          preview.textContent = value ? `${value} year${value === '1' ? '' : 's'}` : emptyValues.experience;
        } else if (key === 'status') {
          preview.textContent = value.replace('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
          preview.className = `status-pill status-${value}`;
        } else {
          preview.textContent = value || emptyValues[key];
        }
      });
      field.addEventListener('change', () => field.dispatchEvent(new Event('input')));
    });

    const photoInput = doctorEditor.querySelector('[data-doctor-photo-input]');
    const photoPreview = doctorEditor.querySelector('[data-doctor-photo-preview]');
    if (photoInput && photoPreview) {
      photoInput.addEventListener('change', () => {
        const [photo] = photoInput.files;
        if (!photo) return;
        photoPreview.src = URL.createObjectURL(photo);
      });
    }
  }

  document.querySelectorAll('[data-tabs]').forEach((tabs) => {
    const buttons = tabs.querySelectorAll('[data-tab]');
    const panels = tabs.querySelectorAll('[data-panel]');
    buttons.forEach((button) => {
      button.addEventListener('click', () => {
        buttons.forEach((item) => {
          const selected = item === button;
          item.classList.toggle('is-active', selected);
          item.setAttribute('aria-selected', String(selected));
        });
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.panel === button.dataset.tab));
      });
    });
  });
});
