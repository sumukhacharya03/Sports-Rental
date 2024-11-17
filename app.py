import streamlit as st
import mysql.connector
import pandas as pd
from mysql.connector import Error
from datetime import datetime, timedelta
import time

def check_student_eligibility(cursor, student_id):
    """Check if student is eligible for new rentals"""
    cursor.execute("SELECT Overdue_Items FROM Student WHERE Student_ID = %s", (student_id,))
    result = cursor.fetchone()
    if result and result[0] >= 3:  # Maximum 3 overdue items allowed
        return False, f"You have {result[0]} overdue items. Please return them before making new reservations."
    return True, "Eligible"

def check_equipment_availability(cursor, equipment_id):
    """Check if equipment is available for reservation"""
    cursor.execute("SELECT Status, Name FROM Equipment WHERE Equipment_ID = %s", (equipment_id,))
    result = cursor.fetchone()
    if not result:
        return False, "Equipment not found"
    if result[0] != 'Available':
        return False, f"{result[1]} is currently {result[0]}"
    return True, "Available"

def make_reservation(cursor, student_id, equipment_id, rental_period):
    """Create a new reservation"""
    # Generate new reservation ID
    cursor.execute("SELECT MAX(Reservation_ID) FROM Reservation")
    max_id = cursor.fetchone()[0] or 3000
    new_reservation_id = max_id + 1
    
    # Create reservation
    insert_query = """
    INSERT INTO Reservation (Reservation_ID, Rental_Period, Return_Status, Date, Equipment_ID, Student_ID) 
    VALUES (%s, %s, 'Pending', CURDATE(), %s, %s)
    """
    cursor.execute(insert_query, (new_reservation_id, rental_period, equipment_id, student_id))
    
    # Update equipment status
    cursor.execute("UPDATE Equipment SET Status = 'Reserved' WHERE Equipment_ID = %s", (equipment_id,))
    
    return new_reservation_id

def convert_to_rental(cursor, reservation_id):
    """Convert a reservation to an active rental"""
    # Get reservation details
    cursor.execute("""
        SELECT R.Equipment_ID, R.Student_ID, R.Rental_Period 
        FROM Reservation R 
        WHERE R.Reservation_ID = %s AND R.Return_Status = 'Pending'
    """, (reservation_id,))
    result = cursor.fetchone()
    
    if not result:
        return False, "Reservation not found or already processed"
    
    equipment_id, student_id, rental_period = result
    
    # Generate new rental ID
    cursor.execute("SELECT MAX(Rental_ID) FROM Rental")
    max_id = cursor.fetchone()[0] or 4000
    new_rental_id = max_id + 1
    
    # Create rental record
    insert_query = """
    INSERT INTO Rental (Rental_ID, Rental_Date, Return_Date, Damage_Report, Student_ID, Equipment_ID) 
    VALUES (%s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL %s DAY), NULL, %s, %s)
    """
    cursor.execute(insert_query, (new_rental_id, rental_period, student_id, equipment_id))
    
    # Update reservation status
    cursor.execute("UPDATE Reservation SET Return_Status = 'In Progress' WHERE Reservation_ID = %s", (reservation_id,))
    
    # Update equipment status
    cursor.execute("UPDATE Equipment SET Status = 'In Use' WHERE Equipment_ID = %s", (equipment_id,))
    
    return True, new_rental_id

def return_equipment(cursor, rental_id, damage_report=None):
    """Process equipment return"""
    # Get rental details
    cursor.execute("""
        SELECT R.Equipment_ID, R.Student_ID, R.Return_Date 
        FROM Rental R 
        WHERE R.Rental_ID = %s AND R.Return_Date >= CURDATE()
    """, (rental_id,))
    result = cursor.fetchone()
    
    if not result:
        return False, "Rental not found or already returned"
    
    equipment_id, student_id, return_date = result
    
    # Update rental record
    cursor.execute("""
        UPDATE Rental 
        SET Return_Date = CURDATE(), 
            Damage_Report = %s 
        WHERE Rental_ID = %s
    """, (damage_report, rental_id))
    
    # Update equipment status based on damage report
    new_status = 'Maintenance' if damage_report and 'damage' in damage_report.lower() else 'Available'
    cursor.execute("""
        UPDATE Equipment 
        SET Status = %s,
            Maintenance_Status = %s 
        WHERE Equipment_ID = %s
    """, (new_status, 'Needs inspection' if damage_report else 'Good', equipment_id))
    
    # Update student's overdue items if returned late
    if datetime.now().date() > return_date:
        cursor.execute("""
            UPDATE Student 
            SET Overdue_Items = Overdue_Items + 1 
            WHERE Student_ID = %s
        """, (student_id,))
    
    return True, "Equipment returned successfully"

# Initialize session state variables if they don't exist
if 'user_type' not in st.session_state:
    st.session_state['user_type'] = None
if 'admin_id' not in st.session_state:
    st.session_state['admin_id'] = None

def verify_admin(admin_id):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="admin_user",
            password="admin",
            database="sports_rental"
        )
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Admin WHERE Admin_ID = %s", (admin_id,))
        admin = cursor.fetchone()
        cursor.close()
        connection.close()
        return admin if admin else None
    except Error as e:
        st.error(f"Error: '{e}'")
        return None

def create_connection(user, password):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user=user,
            password=password,
            database="sports_rental"
        )
        return connection
    except Error as e:
        st.error(f"Error: '{e}'")
        return None

USER_CREDENTIALS = {
    "admin_user": "admin",
    "student_user": "student"
}

# Centered Login Page
if st.session_state['user_type'] is None:
    st.title("Sports Equipment Rental Management System")
    st.subheader("Login to Access the Dashboard")

    user_type_input = st.selectbox("Select User Type", ["admin_user", "student_user"])
    password = st.text_input("Enter Password", type="password")

    if st.button("Login"):
        if user_type_input in USER_CREDENTIALS and password == USER_CREDENTIALS[user_type_input]:
            st.session_state['user_type'] = user_type_input
            st.success(f"🎉 Login successful! Welcome to the {user_type_input.replace('_', ' ').title()} Portal!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Login Failed, Invalid Credentials")

# Admin Selection Page
elif st.session_state['user_type'] == "admin_user" and st.session_state['admin_id'] is None:
    st.title("Admin Selection")
    admin_selection = st.radio("Select Admin ID", [1, 2])
    
    if st.button("Continue"):
        if verify_admin(admin_selection):
            st.session_state['admin_id'] = admin_selection
            st.success(f"Welcome Admin {admin_selection}!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid Admin ID")

# Admin Dashboard
elif st.session_state['user_type'] == "admin_user" and st.session_state['admin_id'] is not None:
    st.title(f"Welcome Admin {st.session_state['admin_id']}!")
    st.sidebar.header("Admin Dashboard")
    
    entity = st.sidebar.selectbox("Select Entity", ["Equipment", "Reservation", "Student", "Rental"])
    operation = st.sidebar.radio("Choose Operation", ["View", "Add", "Update", "Delete"])
    
    connection = create_connection("admin_user", USER_CREDENTIALS["admin_user"])

    if connection:
        cursor = connection.cursor()
        
        # Equipment Operations
        if entity == "Equipment":
            if operation == "View":
                cursor.execute("SELECT * FROM Equipment")
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=["Equipment_ID", "Name", "Type", "Status", "Maintenance_Status", "Admin_ID"])
                st.write(df)

            elif operation == "Add":
                equipment_id = st.number_input("Equipment ID", min_value=1)
                equipment_name = st.text_input("Equipment Name")
                equipment_type = st.text_input("Equipment Type")
                equipment_status = st.text_input("Status")
                equipment_maintenance = st.text_input("Maintenance Status")
                
                if st.button("Add Equipment"):
                    insert_query = """
                    INSERT INTO Equipment (Equipment_ID, Name, Type, Status, Maintenance_Status, Admin_ID) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (equipment_id, equipment_name, equipment_type, equipment_status, 
                                                equipment_maintenance, st.session_state['admin_id']))
                    connection.commit()
                    st.success("Equipment added successfully.")
                    
            elif operation == "Update":
                equipment_id = st.number_input("Enter Equipment ID to Update", min_value=1)
                
                cursor.execute("SELECT * FROM Equipment WHERE Equipment_ID = %s", (equipment_id,))
                data = cursor.fetchone()
                
                if data:
                    name = st.text_input("Equipment Name", value=data[1])
                    equipment_type = st.text_input("Equipment Type", value=data[2])
                    status = st.text_input("Status", value=data[3])
                    maintenance_status = st.text_input("Maintenance Status", value=data[4])

                    if st.button("Update Equipment"):
                        update_query = """
                        UPDATE Equipment 
                        SET 
                            Name = COALESCE(%s, Name),
                            Type = COALESCE(%s, Type),
                            Status = COALESCE(%s, Status),
                            Maintenance_Status = COALESCE(%s, Maintenance_Status),
                            Admin_ID = %s
                        WHERE Equipment_ID = %s
                        """
                        cursor.execute(update_query, (name, equipment_type, status, maintenance_status, 
                                                    st.session_state['admin_id'], equipment_id))
                        connection.commit()
                        st.success("Equipment updated successfully.")
                else:
                    st.error("Equipment not found.")
            
            elif operation == "Delete":
                equipment_id = st.number_input("Enter Equipment ID to Delete", min_value=1)
                
                if st.button("Delete Equipment"):
                    delete_query = "DELETE FROM Equipment WHERE Equipment_ID = %s"
                    cursor.execute(delete_query, (equipment_id,))
                    connection.commit()
                    st.success("Equipment deleted successfully.")

        # Student Operations
        elif entity == "Student":
            if operation == "View":
                cursor.execute("SELECT * FROM Student")
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=["Student_ID", "Name", "Email", "Phone", "Overdue_Items", "Admin_ID"])
                st.write(df)
            
            elif operation == "Add":
                student_id = st.number_input("Student ID", min_value=1)
                name = st.text_input("Student Name")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                overdue_items = st.number_input("Overdue Items", min_value=0)
                
                if st.button("Add Student"):
                    insert_query = """
                    INSERT INTO Student (Student_ID, Name, Email, Phone, Overdue_Items, Admin_ID) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (student_id, name, email, phone, overdue_items, 
                                                st.session_state['admin_id']))
                    connection.commit()
                    st.success("Student added successfully.")
            
            elif operation == "Update":
                student_id = st.number_input("Enter Student ID to Update", min_value=1)
                
                cursor.execute("SELECT * FROM Student WHERE Student_ID = %s", (student_id,))
                data = cursor.fetchone()

                if data:
                    name = st.text_input("Student Name", value=data[1])
                    email = st.text_input("Email", value=data[2])
                    phone = st.text_input("Phone", value=data[3])
                    overdue_items = st.number_input("Overdue Items", min_value=0, value=data[4])

                    if st.button("Update Student"):
                        update_query = """
                        UPDATE Student 
                        SET 
                            Name = COALESCE(NULLIF(%s, ''), Name),
                            Email = COALESCE(NULLIF(%s, ''), Email),
                            Phone = COALESCE(NULLIF(%s, ''), Phone),
                            Overdue_Items = COALESCE(NULLIF(%s, 0), Overdue_Items),
                            Admin_ID = %s
                        WHERE Student_ID = %s
                        """
                        cursor.execute(update_query, (name, email, phone, overdue_items, 
                                                    st.session_state['admin_id'], student_id))
                        connection.commit()
                        st.success("Student updated successfully.")
                else:
                    st.error("Student not found.")

            elif operation == "Delete":
                student_id = st.number_input("Enter Student ID to Delete", min_value=1)
                
                if st.button("Delete Student"):
                    delete_query = "DELETE FROM Student WHERE Student_ID = %s"
                    cursor.execute(delete_query, (student_id,))
                    connection.commit()
                    st.success("Student deleted successfully.")

        # Reservations Operations
        elif entity == "Reservation":
            if operation == "View":
                cursor.execute("SELECT * FROM Reservation")
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=["Reservation_ID", "Rental_Period", "Return_Status", "Date", "Equipment_ID", "Student_ID"])
                st.write(df)
            elif operation == "Add":
                reservation_id = st.number_input("Reservation ID", min_value=1)
                rental_period = st.number_input("Rental Period (in days)", min_value=1)
                return_status = st.selectbox("Return Status", ["Returned", "Pending", "In Progress"])
                date = st.date_input("Date")
                equipment_id = st.number_input("Equipment ID", min_value=1)
                student_id = st.number_input("Student ID", min_value=1)

                if st.button("Add Reservation"):
                    insert_query = """
                    INSERT INTO Reservation (Reservation_ID, Rental_Period, Return_Status, Date, Equipment_ID, Student_ID) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (reservation_id, rental_period, return_status, date, equipment_id, student_id))
                    connection.commit()
                    st.success("Reservation added successfully.")

            elif operation == "Update":
                reservation_id = st.number_input("Enter Reservation ID to Update", min_value=1)

                # Fetch current reservation data for the provided Reservation ID
                cursor.execute("SELECT * FROM Reservation WHERE Reservation_ID = %s", (reservation_id,))
                data = cursor.fetchone()

                if data:
                    rental_period = st.number_input("Rental Period (in days)", value=data[1], min_value=1)
                    return_status = st.selectbox("Return Status", ["Returned", "Pending", "In Progress"], index=["Returned", "Pending", "In Progress"].index(data[2]))
                    date = st.date_input("Date", value=data[3])
                    equipment_id = st.number_input("Equipment ID", value=data[4], min_value=1)
                    student_id = st.number_input("Student ID", value=data[5], min_value=1)

                    if st.button("Update Reservation"):
                        update_query = """
                        UPDATE Reservation
                        SET 
                            Rental_Period = %s,
                            Return_Status = %s,
                            Date = %s,
                            Equipment_ID = %s,
                            Student_ID = %s
                        WHERE Reservation_ID = %s
                        """
                        cursor.execute(update_query, (rental_period, return_status, date, equipment_id, student_id, reservation_id))
                        connection.commit()
                        st.success("Reservation updated successfully.")
                else:
                    st.error("Reservation not found.")

            elif operation == "Delete":
                reservation_id = st.number_input("Enter Reservation ID to Delete", min_value=1)
                
                if st.button("Delete Reservation"):
                    delete_query = "DELETE FROM Reservation WHERE Reservation_ID = %s"
                    cursor.execute(delete_query, (reservation_id,))
                    connection.commit()
                    st.success("Reservation deleted successfully.")
        # Rental Operations
        elif entity == "Rental":
            if operation == "View":
                cursor.execute("SELECT * FROM Rental")
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=["Rental_ID", "Rental_Date", "Return_Date", "Damage_Report", "Student_ID", "Equipment_ID"])
                st.write(df)

            elif operation == "Add":
                rental_id = st.number_input("Rental ID", min_value=1)
                rental_date = st.date_input("Rental Date")
                return_date = st.date_input("Return Date")
                damage_report = st.text_area("Damage Report")
                student_id = st.number_input("Student ID", min_value=1)
                equipment_id = st.number_input("Equipment ID", min_value=1)

                if st.button("Add Rental"):
                    insert_query = """
                    INSERT INTO Rental (Rental_ID, Rental_Date, Return_Date, Damage_Report, Student_ID, Equipment_ID) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (rental_id, rental_date, return_date, damage_report, student_id, equipment_id))
                    connection.commit()
                    st.success("Rental added successfully.")
            elif operation == "Update":
                rental_id = st.number_input("Enter Rental ID to Update", min_value=1)

                # Fetch current rental data for the provided Rental ID
                cursor.execute("SELECT * FROM Rental WHERE Rental_ID = %s", (rental_id,))
                data = cursor.fetchone()

                if data:
                    # Show current values and allow updates
                    rental_date = st.date_input("Rental Date", value=data[1])
                    return_date = st.date_input("Return Date", value=data[2] if data[2] else None)
                    damage_report = st.text_area("Damage Report", value=data[3] if data[3] else "")
                    student_id = st.number_input("Student ID", value=data[4], min_value=1)
                    equipment_id = st.number_input("Equipment ID", value=data[5], min_value=1)

                    if st.button("Update Rental"):
                        update_query = """
                        UPDATE Rental 
                        SET 
                            Rental_Date = %s,
                            Return_Date = %s,
                            Damage_Report = %s,
                            Student_ID = %s,
                            Equipment_ID = %s
                        WHERE Rental_ID = %s
                        """
                        cursor.execute(update_query, (rental_date, return_date, damage_report, student_id, equipment_id, rental_id))
                        connection.commit()
                        st.success("Rental updated successfully.")
                else:
                    st.error("Rental not found.")
            elif operation == "Delete":
                rental_id = st.number_input("Enter Rental ID to Delete", min_value=1)
                
                if st.button("Delete Rental"):
                    delete_query = "DELETE FROM Rental WHERE Rental_ID = %s"
                    cursor.execute(delete_query, (rental_id,))
                    connection.commit()
                    st.success("Rental deleted successfully.")

        # Close the cursor and connection after operations
        cursor.close()
        connection.close()

    # Logout button
    if st.sidebar.button("Logout"):
        del st.session_state['user_type']
        del st.session_state['admin_id']
        st.rerun()

# Student Dashboard
if st.session_state['user_type'] == "student_user":
    st.title("Welcome to the Student Portal!")
    st.sidebar.header("Student Dashboard")
    
    # Get student ID
    student_id = st.number_input("Enter Your Student ID", min_value=1001, step=1, value=1001)
    
    connection = mysql.connector.connect(
        host="localhost",
        user="student_user",
        password="student",
        database="sports_rental"
    )
    
    if connection:
        cursor = connection.cursor()
        
        # Student Information with Alerts
        cursor.execute("""
            SELECT S.*, 
                   COUNT(R.Rental_ID) as Active_Rentals,
                   SUM(CASE WHEN R.Return_Date < CURDATE() THEN 1 ELSE 0 END) as Current_Overdue
            FROM Student S
            LEFT JOIN Rental R ON S.Student_ID = R.Student_ID AND R.Return_Date IS NULL
            WHERE S.Student_ID = %s
            GROUP BY S.Student_ID
        """, (student_id,))
        student_data = cursor.fetchone()
        
        if student_data:
            # Display student info in a clean format
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Student Information")
                st.write(f"Name: {student_data[1]}")
                st.write(f"Email: {student_data[2]}")
                st.write(f"Phone: {student_data[3]}")
            
            with col2:
                st.subheader("Rental Status")
                st.write(f"Active Rentals: {student_data[6]}")
                st.write(f"Overdue Items: {student_data[4]}")
                
                if student_data[4] > 0:
                    st.error(f"⚠️ You have {student_data[4]} overdue items!")
        
        # Tabs for different sections - Added new "Equipment Catalog" tab
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Equipment Catalog", "Make Reservation", "Return Equipment", "My Reservations", "History"])
        
        with tab1:
            st.subheader("Equipment Catalog")
            # Add filters for equipment
            col1, col2 = st.columns(2)
            with col1:
                # Get unique equipment types for filter
                cursor.execute("SELECT DISTINCT Type FROM Equipment ORDER BY Type")
                equipment_types = [type[0] for type in cursor.fetchall()]
                equipment_types.insert(0, "All")
                selected_type = st.selectbox("Filter by Type", equipment_types)
            
            with col2:
                # Filter by availability
                availability_options = ["All", "Available", "In Use", "Reserved", "Maintenance"]
                selected_availability = st.selectbox("Filter by Availability", availability_options)
            
            # Build query based on filters
            query = """
                SELECT 
                    E.Equipment_ID,
                    E.Name,
                    E.Type,
                    E.Status,
                    E.Maintenance_Status,
                    CASE 
                        WHEN R.Return_Date IS NOT NULL THEN DATE_FORMAT(R.Return_Date, '%Y-%m-%d')
                        ELSE 'N/A'
                    END as Next_Available
                FROM Equipment E
                LEFT JOIN Rental R ON E.Equipment_ID = R.Equipment_ID 
                    AND R.Return_Date >= CURDATE()
                WHERE 1=1
            """
            
            params = []
            if selected_type != "All":
                query += " AND E.Type = %s"
                params.append(selected_type)
            
            if selected_availability != "All":
                query += " AND E.Status = %s"
                params.append(selected_availability)
            
            query += " ORDER BY E.Type, E.Name"
            
            cursor.execute(query, params)
            equipment_data = cursor.fetchall()
            
            if equipment_data:
                # Create DataFrame for better display
                df = pd.DataFrame(equipment_data, 
                    columns=["ID", "Name", "Type", "Status", "Maintenance Status", "Next Available"])
                
                # Apply color coding based on status
                def highlight_status(val):
                    if val == 'Available':
                        return 'background-color: #90EE90'  # Light green
                    elif val == 'In Use':
                        return 'background-color: #FFB6C1'  # Light red
                    elif val == 'Reserved':
                        return 'background-color: #FFE4B5'  # Light orange
                    elif val == 'Maintenance':
                        return 'background-color: #B0C4DE'  # Light blue
                    return ''
                
                # Apply styling
                styled_df = df.style.applymap(highlight_status, subset=['Status'])
                
                # Display the table
                st.dataframe(styled_df, use_container_width=True)
                
                # Add summary statistics
                st.subheader("Equipment Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    available_count = len(df[df['Status'] == 'Available'])
                    st.metric("Available", available_count)
                with col2:
                    in_use_count = len(df[df['Status'] == 'In Use'])
                    st.metric("In Use", in_use_count)
                with col3:
                    reserved_count = len(df[df['Status'] == 'Reserved'])
                    st.metric("Reserved", reserved_count)
                with col4:
                    maintenance_count = len(df[df['Status'] == 'Maintenance'])
                    st.metric("In Maintenance", maintenance_count)
            else:
                st.info("No equipment found matching the selected filters.")
        
        with tab2:
            st.subheader("Make a Reservation")
            
            # Check eligibility
            eligible, msg = check_student_eligibility(cursor, student_id)
            if not eligible:
                st.error(msg)
            else:
                # Show available equipment
                cursor.execute("""
                    SELECT E.Equipment_ID, E.Name, E.Type, E.Maintenance_Status
                    FROM Equipment E
                    WHERE E.Status = 'Available'
                    ORDER BY E.Type, E.Name
                """)
                available_equipment = cursor.fetchall()
                
                if available_equipment:
                    equipment_options = {f"{eq[0]} - {eq[1]} ({eq[2]})": eq[0] for eq in available_equipment}
                    selected_equipment = st.selectbox("Select Equipment", list(equipment_options.keys()))
                    rental_period = st.number_input("Rental Period (days)", min_value=1, max_value=14, value=7)
                    
                    if st.button("Make Reservation"):
                        equipment_id = equipment_options[selected_equipment]
                        available, msg = check_equipment_availability(cursor, equipment_id)
                        
                        if available:
                            reservation_id = make_reservation(cursor, student_id, equipment_id, rental_period)
                            st.success(f"Reservation made successfully! ID: {reservation_id}")
                            connection.commit()
                        else:
                            st.error(msg)
                else:
                    st.info("No equipment available for reservation at the moment.")
        
        with tab3:
            st.subheader("Return Equipment")
            cursor.execute("""
                SELECT R.Rental_ID, E.Name, R.Rental_Date, R.Return_Date
                FROM Rental R
                JOIN Equipment E ON R.Equipment_ID = E.Equipment_ID
                WHERE R.Student_ID = %s AND R.Return_Date >= CURDATE()
                AND R.Damage_Report IS NULL
            """, (student_id,))
            active_rentals = cursor.fetchall()
            
            if active_rentals:
                rental_options = {f"{r[0]} - {r[1]} (Due: {r[3]})": r[0] for r in active_rentals}
                selected_rental = st.selectbox("Select Equipment to Return", list(rental_options.keys()))
                damage_report = st.text_area("Damage Report (if any)")
                
                if st.button("Return Equipment"):
                    success, msg = return_equipment(cursor, rental_options[selected_rental], damage_report)
                    if success:
                        st.success(msg)
                        connection.commit()
                    else:
                        st.error(msg)
            else:
                st.info("No equipment to return.")
        
        with tab4:
            st.subheader("My Reservations")
            
            # Fetch all reservations for the student
            cursor.execute("""
                SELECT 
                    R.Reservation_ID,
                    E.Name as Equipment_Name,
                    R.Date as Reservation_Date,
                    R.Rental_Period,
                    R.Return_Status,
                    CASE 
                        WHEN R.Return_Status = 'Pending' THEN DATE_ADD(R.Date, INTERVAL R.Rental_Period DAY)
                        WHEN R.Return_Status = 'In Progress' THEN 
                            (SELECT RNT.Return_Date 
                             FROM Rental RNT 
                             WHERE RNT.Equipment_ID = R.Equipment_ID 
                             AND RNT.Student_ID = R.Student_ID
                             ORDER BY RNT.Rental_Date DESC 
                             LIMIT 1)
                        ELSE NULL
                    END as Due_Date,
                    E.Status as Equipment_Status
                FROM Reservation R
                JOIN Equipment E ON R.Equipment_ID = E.Equipment_ID
                WHERE R.Student_ID = %s
                ORDER BY R.Date DESC
            """, (student_id,))
            
            reservations = cursor.fetchall()
            
            if reservations:
                # Create DataFrame for reservations
                reservations_df = pd.DataFrame(
                    reservations,
                    columns=["Reservation ID", "Equipment", "Reservation Date", 
                            "Rental Period (Days)", "Status", "Due Date", "Equipment Status"]
                )
                
                # Add color coding based on status
                def highlight_status(row):
                    if row['Status'] == 'Pending':
                        return ['background-color: #FFE4B5' if i == 4 else '' for i in range(len(row))]
                    elif row['Status'] == 'In Progress':
                        return ['background-color: #90EE90' if i == 4 else '' for i in range(len(row))]
                    elif row['Status'] == 'Returned':
                        return ['background-color: #B0C4DE' if i == 4 else '' for i in range(len(row))]
                    return ['' for i in range(len(row))]
                
                # Apply styling
                styled_df = reservations_df.style.apply(highlight_status, axis=1)
                
                # Show reservations with filters
                status_filter = st.selectbox(
                    "Filter by Status",
                    ["All", "Pending", "In Progress", "Returned"]
                )
                
                if status_filter != "All":
                    filtered_df = reservations_df[reservations_df['Status'] == status_filter]
                    styled_df = filtered_df.style.apply(highlight_status, axis=1)
                
                # Display the table
                st.dataframe(styled_df, use_container_width=True)
                
                # Show summary statistics
                st.subheader("Reservations Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    pending_count = len(reservations_df[reservations_df['Status'] == 'Pending'])
                    st.metric("Pending Reservations", pending_count)
                
                with col2:
                    active_count = len(reservations_df[reservations_df['Status'] == 'In Progress'])
                    st.metric("Active Rentals", active_count)
                
                with col3:
                    completed_count = len(reservations_df[reservations_df['Status'] == 'Returned'])
                    st.metric("Completed Reservations", completed_count)
                
                # Show upcoming due dates
                upcoming_due = reservations_df[
                    (reservations_df['Status'].isin(['Pending', 'In Progress'])) &
                    (reservations_df['Due Date'].notna())
                ]
                
                if not upcoming_due.empty:
                    st.subheader("Upcoming Due Dates")
                    for _, row in upcoming_due.iterrows():
                        due_date = pd.to_datetime(row['Due Date'])
                        days_left = (due_date - pd.Timestamp.now()).days
                        
                        if days_left < 0:
                            st.error(f"🚨 Overdue: {row['Equipment']} - Due date was {row['Due Date']}")
                        elif days_left <= 2:
                            st.warning(f"⚠️ Due Soon: {row['Equipment']} - Due on {row['Due Date']}")
                        else:
                            st.info(f"📅 {row['Equipment']} - Due on {row['Due Date']}")
            
            else:
                st.info("No reservations found.")

        with tab5:
            st.subheader("Rental History")
            cursor.execute("""
                SELECT R.Rental_ID, E.Name, R.Rental_Date, R.Return_Date, 
                       R.Damage_Report, RV.Return_Status
                FROM Rental R
                JOIN Equipment E ON R.Equipment_ID = E.Equipment_ID
                LEFT JOIN Reservation RV ON R.Equipment_ID = RV.Equipment_ID 
                    AND R.Student_ID = RV.Student_ID
                WHERE R.Student_ID = %s
                ORDER BY R.Rental_Date DESC
            """, (student_id,))
            history = cursor.fetchall()
            
            if history:
                history_df = pd.DataFrame(history, 
                    columns=["Rental ID", "Equipment", "Rental Date", "Return Date", 
                            "Damage Report", "Status"])
                st.dataframe(history_df)
            else:
                st.info("No rental history found.")
        
        cursor.close()
        connection.close()
    
    # Logout button
    if st.sidebar.button("Logout"):
        del st.session_state['user_type']
        st.rerun()