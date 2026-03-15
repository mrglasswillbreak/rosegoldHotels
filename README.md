 **Project Title: Hotel Booking Management System**

**Project Overview:**

The Hotel Booking Management System is a web application designed to streamline the process of managing hotel bookings, reservations, and guest information. Built using Django, a high-level Python web framework, this system provides hotel administrators with a user-friendly interface to efficiently manage bookings and track guest details.

**Key Features:**

- User Authentication
- Booking Management
- Guest Management
- Reservation Management
- Room Inventory Management
- Billing and Invoicing
- Reporting and Analytics

**Technologies Used:**

* Django : Backend web framework for building the application logic and handling HTTP requests.
* HTML/CSS/JavaScript : Frontend technologies for designing the user interface and adding interactive elements.
* Bootstrap : Frontend framework for creating responsive and mobile-friendly designs.
* SQLite/PostgreSQL : Database management systems for storing and retrieving data efficiently.
* Django REST Framework : Optional for creating RESTful APIs for mobile or external applications.

**Target Audience:**

The Hotel Booking Management System targets hotel owners, managers, receptionists, and staff responsible for managing bookings, reservations, and guest interactions. It provides a centralized platform to streamline operations, enhance guest experiences, and improve overall efficiency in hotel management.

**How to run locally:**

- Download the project ZIP file from the repository.
- Extract the downloaded ZIP file to a preferred location on your system.
- Open the extracted folder in your preferred code editor (e.g., Visual Studio Code, Sublime Text, Atom).
- Open a terminal or command prompt within the project directory.
- Install the required dependencies by running the command:
         ```
         pip install -r requirements.txt.
        ```
- Apply migrations to set up the database schema by running:
         ```
         python manage.py migrate.
         ```
- Create a superuser account to access the admin panel:
         ```
         python manage.py createsuperuser.
         ``` 
- Start the development server by running:
         ```
         python manage.py runserver.
        ```
- Open a web browser and navigate to `http://127.0.0.1:8000/` to access the Hotel Booking Management System.

That's it! You've successfully set up and launched the Hotel Booking Management System on your local system.

---

## Deploying on Render

Follow these tailored steps to deploy this project on [Render](https://render.com) after connecting your GitHub account and selecting this repository.

### Prerequisites
- A free [Render](https://render.com) account connected to your GitHub account.
- This repository pushed to GitHub.

### Option A – One-click deploy with `render.yaml` (recommended)

1. **Connect GitHub** – In the Render dashboard click **New → Blueprint** and select this repository.
2. **Render reads `render.yaml`** – It will auto-detect the `render.yaml` at the repo root and pre-fill all settings (build command, start command, environment variables, etc.).
3. **Apply** – Click **Apply** to create the web service. Render will:
   - Install Python 3.9 and all dependencies from `requirements.txt`.
   - Run `python manage.py collectstatic --noinput` and `python manage.py migrate`.
   - Start the app with `gunicorn HotelManagementSystem.wsgi:application`.
4. **Done** – Your app will be live at `https://<service-name>.onrender.com`.

### Option B – Manual deploy via the Render dashboard

1. In the Render dashboard click **New → Web Service**.
2. **Connect the repo** – Select this GitHub repository and click **Connect**.
3. Fill in the following fields:

   | Field | Value |
   |---|---|
   | **Name** | `hotel-management-system` (or any name you like) |
   | **Root Directory** | `Django_practice_Pro_hotel_management_system-main` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `./build.sh` |
   | **Start Command** | `gunicorn HotelManagementSystem.wsgi:application` |
   | **Plan** | Free |

4. **Add environment variables** – Under the *Environment* tab add:

   | Key | Value |
   |---|---|
   | `SECRET_KEY` | Click **Generate** for a random value |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.onrender.com` |
   | `WEB_CONCURRENCY` | `4` |

5. Click **Create Web Service**. Render will clone the repo, run the build script, and start the server.
6. Once the deploy finishes, click the service URL at the top of the dashboard to open your app.

### Optional – Use a PostgreSQL database (persistent data)

By default the app uses SQLite, which is reset whenever Render restarts the service. For persistent data:

1. In the Render dashboard click **New → PostgreSQL** and create a free database.
2. Copy the **Internal Database URL** from the database dashboard.
3. In your web service go to **Environment → Add Environment Variable**:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | *(paste the Internal Database URL)* |

4. Redeploy – the app will automatically switch to PostgreSQL.

### Creating an admin superuser

After the first successful deploy, open the Render **Shell** tab for your web service and run:

```bash
python manage.py createsuperuser
```

Follow the prompts to set an email and password for the admin account, then visit `https://<your-service>.onrender.com/admin/`.

---

**Output Video:**

https://github.com/2200031797KavyaA/Django_practice_Pro_hotel_management_system-main/assets/140434642/8a66963e-96ec-4339-9869-b0a145ff2ba6

