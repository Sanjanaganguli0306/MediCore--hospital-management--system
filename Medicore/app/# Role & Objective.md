# Role & Objective
You are an expert frontend developer and UI/UX engineer. Build a fully responsive, production-ready Hospital Management System dashboard ("City General Admin Portal") using HTML, Tailwind CSS, and vanilla JavaScript, following the exact design specifications below.

# Visual Identity & Design System (Modern Clinical Emerald)
- **Color Mode:** Dark Mode primary (`bg-surface` #081425, `surface-container` #111c2d).
- **Primary Accent:** Calming Emerald / Mint (`#0D9488` / `text-primary`).
- **Typography:** Plus Jakarta Sans (or Inter), clean hierarchy, high contrast for clinical data legibility.
- **Surface & Cards:** Rounded-full / rounded-2xl modern card containers with subtle borders (`border-outline-variant/20`), zero heavy drop shadows (flat clean enterprise aesthetic).

# Layout & Component Architecture
1. **Fixed Left Sidebar (`SideNavBar`)**:
   - Brand Header: "City General" with "Admin Portal" subtext.
   - 5 Navigation Items with icons (Dashboard, Patients, Appointments, Staff, Settings). Dashboard active state highlighted with secondary container background (`bg-secondary-container`).
   - Bottom CTA: "Emergency Alert" high-visibility warning button.
   - User profile badge at the very bottom.
2. **Top Application Bar (`TopAppBar`)**:
   - Fixed top bar with global search bar on the left ("Search patients, doctors, records...").
   - Action buttons on the right: "Add Patient" primary button, Notifications bell, Help icon, and Admin User profile avatar.
3. **Executive Dashboard Content (`/dashboard`)**:
   - **Welcome & Status Banner**: System Operational status badge, welcome greeting ("Welcome back, Dr. Chen"), hospital capacity indicator (84%), and quick action buttons ("Generate Analytics Report", "Manage Roster").
   - **Metrics Grid**: 4 key indicator cards (Total Patients: 1,482; Daily Appointments: 328; Monthly Revenue: $2.48M; Active Doctors: 98) with percentage change indicators.
   - **Today's Appointment Feed**: Real-time queue table displaying Patient Name, Department, Doctor, Time, and Status badges (In Progress, Confirmed, Waiting Room, Checked In, Pending).
   - **Department Workload & Quick Actions**: Side cards for emergency department occupancy and quick action shortcuts (New Patient, E-Prescribe).

# Technical Requirements
- Use Tailwind CSS CDN with custom design tokens matching the clinical emerald theme.
- Ensure fully responsive desktop layout with proper margins (`pl-64` for sidebar offset).
- Include clean interactive hover states and smooth transition classes.
```generate this in our project without anu error