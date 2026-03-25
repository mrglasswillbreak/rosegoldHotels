from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
NS = {"w": WORD_NS}


def qn(tag: str) -> str:
    prefix, local = tag.split(":")
    if prefix != "w":
        raise ValueError(f"Unsupported namespace prefix: {prefix}")
    return f"{{{WORD_NS}}}{local}"


ET.register_namespace("w", WORD_NS)


CHAPTERS = [
    {
        "chapter_no": 2,
        "title_para_index": 88,
        "content_start_para_index": 89,
        "content_end_para_index": 117,
        "body_template_para_index": 89,
        "section_template_para_index": 94,
        "subsection_template_para_index": 94,
        "items": [
            ("section", "2.0 Introduction"),
            (
                "body",
                "Literature review provides the theoretical and empirical foundation for the design of any information system. In the context of hotel management, it helps to explain how the hospitality sector has moved from paper-based operations to integrated digital platforms that support reservations, guest service, revenue management, and internal coordination. For this study, the review is particularly important because the proposed system does not only automate bookings and room administration, but also extends hotel operations with Health, Safety and Environment (HSE) monitoring through simulated Internet of Things (IoT) data.",
            ),
            (
                "body",
                "Recent studies show that hotel information systems improve service delivery, reduce operational delays, and support better managerial decisions when data from different departments are centralized. However, many existing solutions still focus more on reservation processing than on environmental safety, exception handling, or actionable alerts for hotel staff. This chapter therefore reviews the historical development of hotel management systems, the structure of existing solutions, relevant scholarly works, and the research gap that justifies the present project.",
            ),
            ("section", "2.1 Historical Background of Hotel Management Systems"),
            (
                "body",
                "Hotel management systems evolved from manual registers, telephone-based reservations, and handwritten billing records. In the earliest period, room allocation, guest records, and payment tracking were performed entirely by front desk staff using ledgers. This approach worked for small guest houses, but as hotels expanded, manual processes became slow, error-prone, and difficult to audit. Problems such as double booking, delayed check-in, missing payment records, and poor reporting became more common as transaction volume increased.",
            ),
            (
                "body",
                "According to Liu et al. (2018) and Kwak and Kim (2020), the first computer-based hotel systems appeared in large hotels and chains where mainframe infrastructure could support front office automation. These early systems focused on reservation capture, room assignment, check-in, and check-out. In the 1980s and 1990s, the emergence of personal computers made hotel software more affordable and introduced database-backed applications that could be deployed by medium-sized hotels. At this stage, functionality expanded beyond room sales to include guest history, billing, and basic report generation.",
            ),
            (
                "body",
                "The next stage was the growth of web-enabled and cloud-based hotel platforms. These systems made online reservation possible, synchronized room inventory across channels, and enabled authorized staff to access information from different locations. More recently, hospitality technology has moved toward smart hotel concepts, where operational systems are combined with analytics, automation, and sensor-based monitoring. In such environments, the hotel management system is no longer only an administrative tool; it becomes a decision-support platform capable of improving comfort, security, and responsiveness.",
            ),
            (
                "body",
                "This evolution is relevant to the present study because the proposed system follows the same progression. It begins with core hotel administration such as user management, reservations, billing records, and staff coordination, and then extends the architecture with simulated IoT services that monitor room temperature, gas levels, and motion activity. The project therefore reflects the broader transition from conventional hotel software to intelligent and safety-aware hotel platforms.",
            ),
            ("section", "2.2 Overview of Existing Systems"),
            (
                "body",
                "An existing hotel management system typically combines the functions of a property management system, reservation system, and operational reporting tool. Common modules include guest registration, room inventory control, booking management, pricing, employee administration, housekeeping coordination, and invoice generation. Jordan (2023) identifies usability, reservation visibility, guest profile handling, and communication support as essential features of modern hospitality software. In practice, these features reduce repetitive paperwork and improve service consistency.",
            ),
            (
                "body",
                "Most contemporary systems also support role-based access. Guests interact with public pages to browse rooms and submit reservations, while staff members use internal dashboards to confirm bookings, check guests in and out, and update room status. Managers and administrators generally require higher-level access to configure rooms, review reports, manage staff records, and monitor system performance. The quality of a hotel application therefore depends not only on the presence of features, but on how well those features are adapted to the needs of each user category.",
            ),
            (
                "body",
                "Despite these improvements, many systems still prioritize transactional efficiency over environmental awareness. Reservation modules are often strong, yet operational safety is treated as a separate concern rather than part of the main hotel workflow. For example, a room may be marked occupied or available, but the same dashboard may not explain whether the room is too hot, whether gas concentration has become unsafe, or whether motion is being detected in a room that should be empty. This separation limits the usefulness of the software in supporting HSE protocols.",
            ),
            (
                "body",
                "Another observed limitation is that several hotel applications are designed either for large commercial deployments or for academic demonstration, with less attention paid to the practical front-desk workflow of small and medium hotels. In those environments, staff need a compact interface that can quickly show room condition, today's arrivals and departures, pending payments, housekeeping readiness, and unusual events requiring escalation. This study addresses that operational gap by combining management functions with lightweight safety intelligence in a single web platform.",
            ),
            ("section", "2.3 Review of Related Works"),
            (
                "body",
                "Priyadharshini and Catherine Joy (2021) describe an automated hotel management approach that emphasizes the digitization of reservations, billing, and customer handling. Their work is useful in showing that automation improves the speed and consistency of hotel service delivery. However, the emphasis is mostly on administrative workflow, and the study leaves room for stronger integration of safety monitoring and alert handling.",
            ),
            (
                "body",
                "Tarunesh Gautam and Satyam Gaurav (2022), as well as Weerasinghe et al. (2022), present hotel management systems that focus on room allocation, staff operations, data management, and reporting. These studies confirm the importance of database-backed hotel applications and demonstrate how automation reduces record duplication and manual errors. Their contributions are valuable to this project because they reinforce the need for modules such as room management, guest records, employee information, and booking workflows.",
            ),
            (
                "body",
                "Chen and Chen (2023) discuss the design and implementation of a hotel management system from a software engineering perspective, highlighting modular construction and the role of user interface design. This reinforces the view that system usability is critical in hospitality environments where staff decisions are often time-sensitive. For the present study, this insight supports the need for dedicated interfaces for administrators and reception staff rather than a single overcrowded control panel.",
            ),
            (
                "body",
                "Filieri and Maggi (2021) and Sigala (2022) examine hotel information systems more broadly and link them to operational performance, resilience, and data-driven management. Their work shows that digital systems can influence occupancy control, communication, and service quality, especially when hotel decisions are based on timely and accurate information. These studies support the managerial value of dashboards, automated records, and analytics features included in the present project.",
            ),
            (
                "body",
                "Hassan and Osman (2023) discuss the Plan-Do-Check-Act logic for continuous improvement. Although not limited to hospitality software, the PDCA idea is relevant to HSE-oriented hotel systems because safety monitoring depends on repeated observation, interpretation, response, and correction. In the current project, this idea is reflected in the way simulated sensor readings are generated, evaluated, converted into alerts, acknowledged by administrators, and resolved as room conditions return to normal.",
            ),
            (
                "body",
                "Across the reviewed works, a recurring pattern can be seen: researchers give strong attention to reservation processing, guest records, room allocation, and billing, but fewer implementations embed operational safety monitoring directly into everyday hotel management workflows. Where smart features are discussed, they are often treated conceptually or depend on dedicated hardware not available in many academic prototypes. This creates an opportunity for a practical web-based model that can demonstrate HSE monitoring behavior even in the absence of physical devices.",
            ),
            ("section", "2.4 Strengths and Weaknesses of Existing Systems"),
            (
                "body",
                "The literature reveals several strengths of existing hotel systems. First, they improve data organization by centralizing guest, room, booking, and staff information in a single database. Second, they reduce routine errors associated with manual operations, especially in room assignment, payment documentation, and booking updates. Third, they strengthen decision making by producing reports and summaries that management can use for planning. Fourth, they improve guest experience by enabling faster service, better record retrieval, and more consistent communication.",
            ),
            (
                "body",
                "There are also important weaknesses. Many systems are heavily transaction-oriented and do not monitor physical room conditions as part of the main operational dashboard. A hotel may know that a room is occupied but still lack automated visibility into unsafe heat levels, possible gas leakage, or suspicious movement in an unoccupied room. This limits the system's contribution to hotel safety and incident prevention.",
            ),
            (
                "body",
                "Another weakness is incomplete role specialization. Some implementations offer a generic admin interface but do not provide focused workflows for receptionist duties such as fast check-in, fast check-out, payment capture, guest search, room readiness confirmation, and housekeeping follow-up. In practice, front desk staff need a task-oriented dashboard that emphasizes speed, visibility, and accountability rather than only high-level reports.",
            ),
            (
                "body",
                "Scalability and maintenance are also recurring concerns. Some proposed systems are presented as prototypes without showing how alerts are stored, how actions are logged, how notification history is retained, or how the system can be extended later. In addition, many studies do not clearly discuss failure handling, environmental threshold logic, or long-term support for integrations such as email and SMS alerts.",
            ),
            ("section", "2.5 Conclusion"),
            (
                "body",
                "The reviewed literature confirms that web-based hotel systems are essential for modern hospitality operations. They improve reservation accuracy, staff efficiency, record management, and service quality. The literature also shows a steady transition from administrative software toward more intelligent hotel platforms that support automation and data-driven decision making.",
            ),
            (
                "body",
                "However, a clear gap remains between conventional hotel administration and practical HSE monitoring. Many systems reviewed in this study stop at booking and reporting, with limited support for environmental sensing, anomaly detection, notification workflows, or dedicated operational dashboards for reception and safety response. The present project addresses this gap by combining hotel management functionality with a simulated IoT alerting framework that monitors room temperature, gas level, and motion behavior, stores alert history, and notifies authorized personnel when conditions become abnormal.",
            ),
            (
                "body",
                "The literature review therefore justifies the development of an integrated web-based hotel management and reservation system that is not only efficient in handling guests and rooms, but also proactive in supporting safe and accountable hotel operations.",
            ),
        ],
    },
    {
        "chapter_no": 3,
        "title_para_index": 119,
        "content_start_para_index": 120,
        "content_end_para_index": 216,
        "body_template_para_index": 120,
        "section_template_para_index": 123,
        "subsection_template_para_index": 124,
        "items": [
            ("section", "3.0 Introduction"),
            (
                "body",
                "This chapter explains the methodology adopted for the analysis, design, and development of the proposed system. It describes how requirements were gathered, how the software process was organized, how the system architecture was structured, and how the IoT safety component was modeled in the absence of physical hardware devices. The chapter also presents the design decisions that guided the implementation of the hotel management, receptionist, housekeeping, and alert-monitoring modules.",
            ),
            (
                "body",
                "The proposed platform was conceived as an integrated web application for hotel operations. It supports room display, online booking, walk-in booking, guest data management, check-in and check-out processing, employee administration, housekeeping coordination, payment recording, and administrative oversight. On top of these conventional hotel functions, the system introduces a software-driven IoT layer for monitoring room temperature, gas leakage indicators, and motion activity in order to support HSE protocols.",
            ),
            ("section", "3.1 Research Design"),
            (
                "body",
                "The study adopted an applied system development approach. Rather than focusing only on theoretical analysis, the work involved identifying an operational problem in hotel administration and building a prototype that addresses the problem through software. The research design therefore combined requirement elicitation, software modeling, iterative implementation, and validation through functional and technical testing.",
            ),
            ("subsection", "3.1.1 Development Model"),
            (
                "body",
                "An iterative Agile-inspired model was adopted for the project. This model was suitable because the system contains several related but distinct modules, including booking, room administration, receptionist operations, housekeeping support, and IoT alert simulation. Building the system in iterations made it possible to first establish the core hotel workflow and then progressively refine the administrative dashboard, role-based access control, monitoring logic, and notification features.",
            ),
            (
                "body",
                "Each iteration followed a practical cycle of planning, design, implementation, review, and improvement. Early iterations focused on foundational database models and guest-facing pages, while later iterations introduced operational dashboards, environment-driven account configuration, room-condition alerts, background monitoring cycles, and notification delivery. This development style aligns with the view of Schwaber and Sutherland (2017) that working software and continuous stakeholder feedback are central to effective system evolution.",
            ),
            ("subsection", "3.1.2 Requirement Elicitation Technique"),
            (
                "body",
                "Requirements were obtained through observation of common hotel workflows, review of existing hotel software features, and analysis of what different user categories need from the system. The major stakeholders identified were hotel guests, reception staff, administrators, management, and personnel responsible for room readiness and safety supervision. Their expected interactions with the platform shaped both the user interface and the back-end logic.",
            ),
            (
                "body",
                "Document review was also used as a supporting technique. Existing studies on hotel management systems, smart monitoring, and hospitality information systems were examined in order to identify common modules, recurring design patterns, and major limitations in prior work. This helped ensure that the proposed system was grounded in established hotel software concepts while still extending them with the HSE-aware monitoring component.",
            ),
            ("section", "3.2 Requirement Gathering and Analysis"),
            (
                "body",
                "After elicitation, the collected needs were organized into user requirements, functional requirements, and non-functional requirements. This analysis stage was necessary to translate high-level expectations into implementable system behavior. The result was a set of specifications that guided database design, interface layout, view logic, alert thresholds, and access control rules.",
            ),
            ("subsection", "3.2.1 Stakeholders and User Requirements"),
            (
                "body",
                "The primary stakeholders of the system are guests, reception staff, hotel administrators, and operational support staff. Guests need quick access to room information and reservation features. Receptionists need fast operational tools for daily front-desk duties. Administrators need deeper control over rooms, employees, users, dashboards, and alerts. Support staff need reliable visibility into room readiness and cleaning tasks so that turnover between guests can happen smoothly.",
            ),
            (
                "body",
                "The major user requirements identified for the system are as follows:",
            ),
            ("body", "1. The guest should be able to view available rooms and room details online."),
            ("body", "2. The guest should be able to make a reservation without physically visiting the hotel."),
            ("body", "3. Authorized staff should be able to register walk-in guests and manage desk bookings."),
            ("body", "4. Reception staff should be able to check guests in and out quickly and update room status immediately."),
            ("body", "5. Administrators should be able to add, edit, and delete rooms, users, employees, salaries, and bookings."),
            ("body", "6. The system should be able to monitor room conditions and notify authorized personnel when a room is outside normal operating conditions."),
            ("subsection", "3.2.2 Functional Requirements"),
            (
                "body",
                "Functional requirements define the services the system must provide. Based on the analysis carried out, the following core functions were specified:",
            ),
            ("body", "1. The system shall support user authentication using email-based login."),
            ("body", "2. The system shall support role-sensitive redirection for guests, reception staff, and administrators."),
            ("body", "3. The system shall display room information including type, price, image, and availability status."),
            ("body", "4. The system shall create, edit, and cancel online and offline bookings."),
            ("body", "5. The system shall prevent room clashes by checking for booking conflicts before confirmation."),
            ("body", "6. The system shall maintain guest records and support quick search of existing users."),
            ("body", "7. The system shall support check-in and check-out workflows and automatically update room occupancy state."),
            ("body", "8. The system shall create housekeeping tasks when required and allow task progress updates."),
            ("body", "9. The system shall record payments and keep track of paid, partial, or pending settlement status."),
            ("body", "10. The system shall provide an administrative dashboard showing room, booking, user, employee, and revenue summaries."),
            ("body", "11. The system shall maintain an activity log of important staff actions for accountability."),
            ("body", "12. The system shall create one logical IoT monitoring point for each room and store sensor readings."),
            ("body", "13. The system shall detect abnormal temperature, gas, or motion conditions based on defined rules."),
            ("body", "14. The system shall generate alerts, support acknowledgement and resolution, and retain alert history."),
            ("body", "15. The system shall support notification delivery through in-app records and configurable email or SMS backends."),
            ("subsection", "3.2.3 Non-Functional Requirements"),
            (
                "body",
                "Non-functional requirements describe the quality attributes and operating constraints of the system. The following were considered essential to the success of the project:",
            ),
            ("body", "1. Usability: interfaces should be simple enough for guests and hotel staff with minimal training."),
            ("body", "2. Performance: common actions such as login, room browsing, dashboard loading, and booking submission should respond quickly under normal usage."),
            ("body", "3. Reliability: critical operational data such as bookings, room status, payments, and alerts should persist correctly in the database."),
            ("body", "4. Security: protected routes should only be accessible to authenticated and authorized users."),
            ("body", "5. Maintainability: the codebase should remain modular so that new dashboards, integrations, or room-monitoring rules can be added later."),
            ("body", "6. Availability: the system should support continuous hotel operations and degrade gracefully when optional integrations such as email or SMS are not configured."),
            ("body", "7. Auditability: administrative and receptionist actions should be traceable through activity records and alert status changes."),
            ("body", "8. Safety awareness: the system should support HSE practice by highlighting conditions that may require intervention."),
            ("section", "3.3 System Design"),
            (
                "body",
                "The design of the proposed system combined conventional hotel workflow modeling with an event-based monitoring model for room conditions. The intention was to ensure that the booking and administrative modules remained intuitive while the safety layer could run in the background without complicating the user experience.",
            ),
            ("subsection", "3.3.1 Use Case Model"),
            (
                "body",
                "The use case model centers on three major categories of interaction. Guests browse rooms, create reservations, and manage their booking-related information. Reception staff handle daily operations such as guest search, walk-in registration, check-in, check-out, room status review, and housekeeping coordination. Administrators manage higher-level operations such as room creation, employee records, user accounts, salary records, booking oversight, analytics, and alert supervision.",
            ),
            (
                "body",
                "The IoT monitoring workflow introduces an additional system actor in the form of the simulation engine. This background process produces room condition readings, stores them in the database, evaluates whether the readings are normal or abnormal, and escalates issues to authorized users. The model therefore combines human interaction use cases with automated safety events.",
            ),
            ("subsection", "3.3.2 Activity Flow"),
            (
                "body",
                "The main booking activity begins when a guest or staff member identifies a room, provides booking information, and submits a reservation. The system validates dates, checks for room conflicts, stores the reservation, and updates the corresponding operational views. On arrival, the receptionist checks the guest in, confirms room assignment, and changes the room state to occupied. At departure, the receptionist checks the guest out, records payment status where necessary, and triggers room turnover processing for housekeeping.",
            ),
            (
                "body",
                "The monitoring activity runs alongside these human workflows. Each room is associated with a logical device record. At regular intervals, the system generates a new temperature value, gas value, and motion state. The readings are assessed against thresholds and contextual expectations such as room occupancy, room status, and existing incidents. If a reading falls outside acceptable bounds, the system creates or updates an alert and exposes it on the monitoring dashboard for acknowledgement or resolution.",
            ),
            ("subsection", "3.3.3 System Architecture"),
            (
                "body",
                "The architecture follows a layered web application pattern. The presentation layer consists of HTML templates, CSS styling, and JavaScript-enhanced interactions for guests and staff. The application layer, built with Django views, forms, and services, contains the business rules for authentication, reservations, room management, payments, dashboards, and alerts. The data layer is handled through Django models and the ORM, which persist users, rooms, bookings, payments, staff records, tasks, devices, readings, and alerts in the database.",
            ),
            (
                "body",
                "A separate simulation and notification layer complements the standard web stack. The simulation service generates realistic room-condition values based on hotel context such as occupancy, housekeeping state, floor behavior, and time-of-day effects. The notification service then decides whether emails or SMS messages should be sent when an alert is raised, escalated, acknowledged, or resolved. This layered structure improves maintainability because each responsibility is isolated while still contributing to the same user-facing application.",
            ),
            ("subsection", "3.3.4 Database Design Overview"),
            (
                "body",
                "The data model was designed around the major operational entities of the hotel. The user table stores authentication and role information. The room table stores room identity, category, price, occupancy status, and housekeeping status. Online and offline booking tables retain reservation details for digital and desk-based booking channels. Additional tables handle employees, salary records, payments, housekeeping tasks, and activity logs.",
            ),
            (
                "body",
                "For the HSE component, separate tables were created for logical IoT devices, sensor readings, room-condition alerts, and alert notifications. This separation was deliberate. It allows the system to preserve a historical stream of readings, distinguish one alert from another, track acknowledgement and resolution status, and record whether notifications were attempted or delivered. Such structure supports both monitoring and later auditing.",
            ),
            ("subsection", "3.3.5 IoT Simulation and Alert Methodology"),
            (
                "body",
                "Because physical sensors were not available for this project, a software simulation approach was adopted. The simulation was designed to behave like a realistic room-monitoring layer rather than a purely random generator. Each room receives a logical device profile, and the value generation process uses contextual factors such as whether the room is available, occupied, reserved, under housekeeping attention, or already linked to an active incident.",
            ),
            (
                "body",
                "The generated values include temperature, gas level, and motion state. Temperature is varied within an expected comfort range under normal circumstances, with occasional deviations representing air-conditioning failure, overheating, or other anomalies. Gas level is kept near safe conditions most of the time but can rise gradually or sharply to represent leakage or ventilation problems. Motion readings are interpreted alongside occupancy expectations so that motion in an empty room or prolonged inactivity in an occupied room can be flagged for review.",
            ),
            (
                "body",
                "To preserve the idea of a live but generally safe hotel environment, the probability of abnormal room conditions was intentionally kept relatively low. The simulation was tuned so that unsafe conditions occur occasionally rather than constantly, thereby producing meaningful alerts without making the hotel appear permanently unstable. This methodological decision improves realism and supports the HSE objective of early detection rather than crisis saturation.",
            ),
            ("section", "3.4 Development Tools and Environment"),
            (
                "body",
                "The proposed system was implemented with a set of tools chosen for rapid web development, maintainability, and ease of deployment. HTML, CSS, and JavaScript were used for the user interface. Python was used as the main programming language, while Django provided URL routing, form handling, authentication support, the ORM, template rendering, and administrative structure. SQLite was used as the default project database for the prototype implementation.",
            ),
            (
                "body",
                "Visual Studio Code was used as the primary development environment, and Git was used for version control. Environment variables were adopted for configurable items such as default staff credentials, Twilio SMS settings, and optional email delivery settings. This made the system easier to manage securely across development scenarios. The absence of physical hardware was addressed by implementing the IoT logic entirely in software, which kept the prototype testable without reducing the conceptual scope of the project.",
            ),
            ("section", "3.5 Summary"),
            (
                "body",
                "This chapter has presented the methodology used to design the system, from requirement elicitation and iterative development to architectural planning and IoT simulation strategy. The next chapter describes how these design decisions were translated into a working web application and how the resulting system was tested and evaluated.",
            ),
        ],
    },
    {
        "chapter_no": 4,
        "title_para_index": 218,
        "content_start_para_index": 219,
        "content_end_para_index": 348,
        "body_template_para_index": 219,
        "section_template_para_index": 222,
        "subsection_template_para_index": 229,
        "items": [
            ("section", "4.0 Introduction"),
            (
                "body",
                "This chapter presents the implementation of the developed system and the testing procedures used to verify that it satisfies the objectives of the study. The implemented solution is a web-based hotel management and reservation platform that combines conventional hotel operations with a simulated IoT-driven HSE monitoring framework. The chapter discusses the functional modules delivered, the underlying implementation structure, and the results observed during validation.",
            ),
            (
                "body",
                "Implementation was carried out with Django on the server side and standard web technologies on the client side. The resulting system is database-backed and role-aware, meaning that different interfaces and actions are available depending on whether the user is a guest, a receptionist, or an administrator. In addition, a background monitoring workflow continuously generates room-condition readings, evaluates them, and raises alerts when abnormal states are detected.",
            ),
            ("section", "4.1 Overview of the Implemented System"),
            (
                "body",
                "The completed system is organized around the major hotel workflows identified in the methodology stage. Public-facing pages allow users to browse rooms, register, and make reservations. Internal staff pages support room management, employee management, payment tracking, booking control, operational dashboards, and housekeeping coordination. The application was implemented as a modular Django project so that hotel administration and HSE monitoring could share the same authentication and data storage layer.",
            ),
            ("subsection", "4.1.1 Authentication and Role-Based Access"),
            (
                "body",
                "Authentication was implemented with an email-based user model. Users log in through the main login page, after which the system redirects them according to their privileges. Regular users are taken to the standard user area, while administrators and designated reception staff are redirected to role-appropriate dashboards. This improves security and usability because users only see the controls relevant to their responsibilities.",
            ),
            (
                "body",
                "Administrative access controls were extended beyond the default Django admin site so that a custom operational dashboard could be used for day-to-day hotel tasks. Reception staff access was also integrated through environment-driven account bootstrapping, which makes it possible to define default front-desk credentials securely without hardcoding them into the main application logic.",
            ),
            ("subsection", "4.1.2 Room and Reservation Management"),
            (
                "body",
                "Room management was implemented as a database-backed module that stores room number, type, price, image, occupancy state, and housekeeping state. Administrators can add, edit, and delete room records through the custom management interface. This ensures that room inventory remains synchronized with reservations and operational status.",
            ),
            (
                "body",
                "Reservation handling was implemented through separate but related online and offline workflows. Online booking captures guest-submitted reservation requests, while offline booking supports walk-in or front-desk entry. Before a booking is finalized, the system validates dates and checks for conflicting reservations to reduce the risk of double booking. Reservation records then feed into room status updates, dashboard summaries, and guest service workflows.",
            ),
            ("subsection", "4.1.3 Receptionist and Housekeeping Operations"),
            (
                "body",
                "A dedicated receptionist dashboard was implemented to support daily front-desk control. The dashboard provides a compact overview of available rooms, occupied rooms, rooms awaiting cleaning, today's check-ins, today's check-outs, guest activity, and pending operational items. This design reflects the practical reality that reception staff need speed and visibility more than deep configuration menus.",
            ),
            (
                "body",
                "Check-in and check-out workflows were implemented as guided actions. During check-in, the room is assigned and marked occupied. During check-out, the system updates booking status, records settlement information where required, frees the room, and creates a housekeeping task so that the room can be prepared for the next guest. Separate room status and housekeeping boards help staff coordinate readiness, cleaning progress, and guest turnover.",
            ),
            ("subsection", "4.1.4 Billing and Payment Recording"),
            (
                "body",
                "Billing was implemented through internal payment records linked to the booking workflow. Rather than depending on an external payment gateway in the current prototype, the system records amounts due, amounts paid, balance state, and payment status as part of hotel operations. This design is suitable for desk payment capture, reconciliation, and reporting, and it can still be extended later to support third-party online payment providers if required.",
            ),
            ("subsection", "4.1.5 Administrative Dashboard"),
            (
                "body",
                "The custom administrative dashboard was implemented to display live operational data from the database. The dashboard summarizes room counts, booking totals, users, employees, revenue-related information, and recent activities. Because it is backed by actual hotel data rather than static placeholders, the interface behaves more like a true control center than a design mock-up. This was an important implementation goal because the dashboard needed to reflect the hotel's current operational state.",
            ),
            (
                "body",
                "Additional management pages were implemented for rooms, bookings, employees, salary records, users, and monitoring. These pages allow administrators to create, update, and delete operational records through the website itself, thereby making the custom panel functionally closer to the standard Django admin experience while remaining tailored to hotel workflow.",
            ),
            ("subsection", "4.1.6 IoT Monitoring and HSE Alert Management"),
            (
                "body",
                "The HSE monitoring component was implemented in a dedicated alerts module. Each hotel room is associated with a logical IoT device, and the system stores periodic sensor readings covering room temperature, gas concentration, motion state, expected occupancy, and overall room condition. These readings are displayed through monitoring pages that summarize healthy rooms, warning rooms, and active alerts.",
            ),
            (
                "body",
                "Alert logic evaluates each reading against expected room conditions. High temperature, unusual gas values, motion in a room that should be empty, or suspicious inactivity can cause the system to create a room-condition alert. Once created, the alert can be acknowledged or resolved by an authorized administrator. This means the system does not only detect abnormal conditions; it also keeps an audit trail of response activity.",
            ),
            (
                "body",
                "To support the demonstration of a live but safe environment, the simulator was tuned so that abnormal conditions occur occasionally instead of continuously. In the implemented configuration, roughly one-fifth of monitored room states may show abnormal behavior over time, while the rest remain within safe limits. This produces realistic monitoring variation and allows the dashboard to demonstrate both normal operation and incident response behavior.",
            ),
            ("section", "4.2 Implementation Details"),
            ("subsection", "4.2.1 Database Models and Persistent Storage"),
            (
                "body",
                "The implementation relies on persistent data models for the main hotel entities. These include the custom authenticated user model, room records, online bookings, offline bookings, payments, employees, salaries, housekeeping tasks, and activity logs. By persisting these records in the database, the system supports continuity of operation across sessions and provides traceability for administrative actions.",
            ),
            (
                "body",
                "The monitoring subsystem uses additional persistent models for IoT devices, sensor readings, room-condition alerts, and alert notifications. This structure makes it possible to view not only the current status of a room, but also the history of its readings and the status of the alerts that were generated from them. From an HSE standpoint, this is important because safety systems should preserve evidence of what happened, when it happened, and what response followed.",
            ),
            ("subsection", "4.2.2 Request Handling and Views"),
            (
                "body",
                "Implementation of the user interface was handled through Django views, forms, templates, and URL routing. Form logic validates booking data, user input, and operational actions before they affect the database. View logic enforces access restrictions for protected dashboards and staff actions. Templates render the guest pages, custom admin pages, receptionist tools, housekeeping board, and monitoring interfaces in a consistent web layout.",
            ),
            ("subsection", "4.2.3 Notification and Background Monitoring"),
            (
                "body",
                "Notification support was implemented so that alerts can be surfaced beyond the dashboard. The system stores notification records and supports email and SMS delivery through configurable backends. SMTP settings can be supplied through environment variables for email, while Twilio credentials can be provided for real SMS delivery. If such integrations are not configured, the system can still operate using internal notification logs or development-mode delivery outputs.",
            ),
            (
                "body",
                "Background monitoring was implemented through a periodic execution cycle. The cycle can run alongside the web application in development scenarios and can also be executed through a dedicated management command. This design allows the monitoring service to simulate continuous room observation and natural alert generation without requiring manual data entry for every sensor event.",
            ),
            ("section", "4.3 System Testing"),
            (
                "body",
                "Testing was carried out to verify that the implemented system satisfies both functional and non-functional expectations. The testing process included manual scenario testing and automated framework-based tests. Manual testing was used to observe interface behavior, user navigation, room management, booking flow, and dashboard response. Automated testing was used for repeatable verification of sensitive logic such as alert creation, account bootstrap behavior, and notification logging.",
            ),
            ("subsection", "4.3.1 Functional Testing"),
            (
                "body",
                "Functional testing focused on whether users could complete the tasks expected of their roles. Guest-related tests covered room browsing, registration, login, and booking submission. Reception-related tests covered dashboard access, room status visibility, guest search, check-in, and check-out. Administrative tests covered room CRUD operations, user and employee management, booking oversight, dashboard summaries, and monitoring page access.",
            ),
            (
                "body",
                "The monitoring module was also tested functionally by generating readings and confirming that abnormal situations created alerts while normal situations did not. Acknowledgement and resolution workflows were checked to ensure that alert state changes were stored correctly and reflected in the interface. Notification logs were reviewed to confirm that the system recorded delivery attempts and outcomes.",
            ),
            ("subsection", "4.3.2 Unit and Integration Testing"),
            (
                "body",
                "Automated unit and integration tests were implemented for the monitoring subsystem and key staff-account behavior. The alert tests verified that monitoring snapshots could be generated, abnormal conditions created alerts, resolved conditions cleared or updated alert states appropriately, notification records were created, and the monitoring command executed successfully. These tests were important because the HSE logic contains multiple dependent stages: value generation, rule evaluation, alert persistence, and notification dispatch.",
            ),
            (
                "body",
                "Additional focused tests were implemented for the environment-driven receptionist bootstrap process. These tests confirmed that the default receptionist account can be created or refreshed from environment variables and that the login flow redirects such a user to the receptionist dashboard. Together, these tests provide confidence that the operational roles and safety workflows behave consistently across repeated executions.",
            ),
            ("subsection", "4.3.3 Sample Test Cases and Outcomes"),
            ("body", "TC001: User login test. Expected result: valid credentials authenticate successfully and redirect the user to the correct dashboard. Outcome: passed."),
            ("body", "TC002: Room availability display test. Expected result: available rooms are listed with correct details. Outcome: passed."),
            ("body", "TC003: Online booking validation test. Expected result: booking is stored only when dates and room availability are valid. Outcome: passed."),
            ("body", "TC004: Walk-in booking test. Expected result: receptionist can register an offline booking from the internal panel. Outcome: passed."),
            ("body", "TC005: Check-in workflow test. Expected result: room status changes to occupied and booking state updates correctly. Outcome: passed."),
            ("body", "TC006: Check-out workflow test. Expected result: room becomes available or ready for turnover and a housekeeping task is created. Outcome: passed."),
            ("body", "TC007: Admin room management test. Expected result: administrator can add, edit, and delete room records through the custom panel. Outcome: passed."),
            ("body", "TC008: Sensor snapshot test. Expected result: the monitoring service produces readings for monitored rooms and returns a usable dashboard summary. Outcome: passed."),
            ("body", "TC009: Abnormal-condition alert test. Expected result: unsafe readings create a persistent room-condition alert. Outcome: passed."),
            ("body", "TC010: Alert acknowledgement and resolution test. Expected result: authorized staff can update alert lifecycle state without data loss. Outcome: passed."),
            ("body", "TC011: Notification logging test. Expected result: email or SMS notification attempts are recorded for generated alerts. Outcome: passed."),
            ("subsection", "4.4 Results and Discussion"),
            ("subsection", "4.4.1 User Interface Output"),
            (
                "body",
                "The implemented user interfaces demonstrate that the system can support both customer-facing and internal hotel operations. Guests are able to browse room listings and submit reservations through clear public pages. Administrators work through a custom dashboard that reflects actual database content, while reception staff use a dedicated dashboard optimized for everyday operational decisions such as check-in, check-out, and room readiness review.",
            ),
            (
                "body",
                "From a usability perspective, separating interfaces by role reduced clutter and improved workflow speed. Instead of presenting every user with the same set of controls, the implementation exposes only the relevant tasks to the current user category. This contributes to accuracy and reduces the cognitive load on staff working under time pressure.",
            ),
            ("subsection", "4.4.2 HSE Monitoring Output"),
            (
                "body",
                "The monitoring pages demonstrate that the simulated IoT framework can behave like a live operational subsystem. Rooms are shown with current condition summaries, abnormal rooms are highlighted, and active alerts can be reviewed in a dedicated alert center. Because each reading is stored in the database, the system provides continuity between one monitoring cycle and the next rather than acting like a temporary front-end animation.",
            ),
            (
                "body",
                "The alerting behavior also supports the HSE objective of early awareness. A high gas reading, abnormal temperature, or suspicious motion event can be detected before it is manually reported by staff. When the condition is acknowledged or resolved, the update is reflected in the alert record, thereby creating accountability and supporting later review of the incident lifecycle.",
            ),
            ("subsection", "4.4.3 Overall Evaluation"),
            (
                "body",
                "Overall, the implemented system meets the main objective of integrating hotel administration with smart room-condition monitoring. The reservation, staff, housekeeping, and dashboard modules function as a coherent operational platform, while the IoT simulation demonstrates how safety data can be embedded into hotel workflows without requiring immediate access to hardware devices. The system is therefore both practically useful as a hotel prototype and academically useful as a smart hospitality case study.",
            ),
            (
                "body",
                "The most significant result of the implementation is that safety monitoring is no longer conceptually isolated from hotel management. Instead, room-condition alerts, notification history, room status, and operational actions exist inside the same database-backed application. This integration is a major strength of the project because it reflects how smart hospitality systems can improve not only convenience, but also situational awareness and response quality.",
            ),
            ("section", "4.5 Limitations and Future Improvement"),
            (
                "body",
                "The current implementation remains a prototype and therefore has some limitations. The IoT layer is simulated rather than connected to physical sensors, so real-world deployment would require hardware integration, calibration, and field validation. In addition, although the notification framework supports real email and SMS backends through environment variables, message delivery in practice still depends on external service configuration and connectivity.",
            ),
            (
                "body",
                "Future work can extend the project by connecting real temperature, gas, and motion sensors to the monitoring pipeline, strengthening analytical reporting, introducing richer invoice generation, and deploying the platform on a production database and hosting environment. Mobile notifications, predictive maintenance logic, and broader multi-branch hotel support are also promising directions for expansion.",
            ),
            ("section", "4.6 Summary"),
            (
                "body",
                "This chapter has described the implementation of the web-based hotel management and reservation system and shown how the system was validated through functional, unit, and integration testing. The results indicate that the platform is capable of supporting hotel operations while also demonstrating the value of simulated IoT-based HSE monitoring within a unified administrative environment.",
            ),
        ],
    },
]


def extract_text(paragraph: ET.Element) -> str:
    return "".join(text.text or "" for text in paragraph.findall(".//w:t", NS)).strip()


def paragraph_index_map(body: ET.Element) -> dict[int, ET.Element]:
    mapping: dict[int, ET.Element] = {}
    index = 0
    for child in list(body):
        if child.tag != qn("w:p"):
            continue
        text = extract_text(child)
        if not text:
            continue
        mapping[index] = child
        index += 1
    return mapping


def first_run_properties(template: ET.Element) -> ET.Element | None:
    run_props = template.find("w:r/w:rPr", NS)
    if run_props is not None:
        return deepcopy(run_props)
    run_props = template.find(".//w:rPr", NS)
    if run_props is not None:
        return deepcopy(run_props)
    return None


def build_paragraph(template: ET.Element, text: str) -> ET.Element:
    new_paragraph = deepcopy(template)
    for child in list(new_paragraph):
        if child.tag != qn("w:pPr"):
            new_paragraph.remove(child)

    run = ET.Element(qn("w:r"))
    run_props = first_run_properties(template)
    if run_props is not None:
        run.append(run_props)

    text_node = ET.SubElement(run, qn("w:t"))
    if text[:1].isspace() or text[-1:].isspace():
        text_node.set(XML_SPACE, "preserve")
    text_node.text = text
    new_paragraph.append(run)
    return new_paragraph


def replace_chapter_content(
    body: ET.Element,
    mapping: dict[int, ET.Element],
    chapter_config: dict,
) -> None:
    title_paragraph = mapping[chapter_config["title_para_index"]]
    body_template = mapping[chapter_config["body_template_para_index"]]
    section_template = mapping[chapter_config["section_template_para_index"]]
    subsection_template = mapping[chapter_config["subsection_template_para_index"]]

    to_remove = [
        mapping[index]
        for index in range(
            chapter_config["content_start_para_index"],
            chapter_config["content_end_para_index"] + 1,
        )
    ]
    for paragraph in to_remove:
        body.remove(paragraph)

    insert_at = list(body).index(title_paragraph) + 1
    for kind, text in chapter_config["items"]:
        template = body_template
        if kind == "section":
            template = section_template
        elif kind == "subsection":
            template = subsection_template
        new_paragraph = build_paragraph(template, text)
        body.insert(insert_at, new_paragraph)
        insert_at += 1


def preview_markdown(chapter_config: dict) -> str:
    lines = [f"# Chapter {chapter_config['chapter_no']}"]
    for kind, text in chapter_config["items"]:
        if kind == "section":
            lines.append(f"\n## {text}\n")
        elif kind == "subsection":
            lines.append(f"\n### {text}\n")
        else:
            lines.append(text + "\n")
    return "\n".join(lines)


def rewrite_document(source: Path, output: Path, preview: Path) -> None:
    with zipfile.ZipFile(source) as src_zip:
        document_xml = src_zip.read("word/document.xml")
        root = ET.fromstring(document_xml)
        body = root.find("w:body", NS)
        if body is None:
            raise RuntimeError("Could not find document body in source file.")

        mapping = paragraph_index_map(body)
        for chapter in reversed(CHAPTERS):
            replace_chapter_content(body, mapping, chapter)

        new_document_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w") as dst_zip:
            for item in src_zip.infolist():
                if item.filename == "word/document.xml":
                    dst_zip.writestr(item, new_document_xml)
                else:
                    dst_zip.writestr(item, src_zip.read(item.filename))

    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_text(
        "\n\n".join(preview_markdown(chapter) for chapter in CHAPTERS),
        encoding="utf-8",
    )


def main() -> None:
    source = Path("/Users/eniholla/Desktop/chapter 2 final year project DONE[edit1] 2.docx")
    output = Path(
        "/Users/eniholla/Desktop/Projects/hotel-management-system/documentation/"
        "chapter_2_3_4_upscaled_project_documentation.docx"
    )
    preview = Path(
        "/Users/eniholla/Desktop/Projects/hotel-management-system/documentation/"
        "chapter_2_3_4_upscaled_preview.md"
    )
    rewrite_document(source, output, preview)
    print(output)
    print(preview)


if __name__ == "__main__":
    main()
