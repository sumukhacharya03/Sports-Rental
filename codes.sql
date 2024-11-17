-- Creation and usage of database
create database sports_rental;
use sports_rental;

-- Student Table
CREATE TABLE Student (
    Student_ID INT PRIMARY KEY,
    Name VARCHAR(50),
    Email VARCHAR(50),
    Phone VARCHAR(15),
    Overdue_Items INT DEFAULT 0,
    Admin_ID INT,
    FOREIGN KEY (Admin_ID) REFERENCES Admin(Admin_ID)
);

-- Admin Table
CREATE TABLE Admin (
    Admin_ID INT PRIMARY KEY,
    Name VARCHAR(50),
    Email VARCHAR(50),
    Phone VARCHAR(15)
);

-- Equipment Table
CREATE TABLE Equipment (
    Equipment_ID INT PRIMARY KEY,
    Name VARCHAR(50),
    Type VARCHAR(30),
    Status VARCHAR(20),
    Maintenance_Status VARCHAR(20),
    Admin_ID INT,
    FOREIGN KEY (Admin_ID) REFERENCES Admin(Admin_ID)
);

-- Reservation Table
CREATE TABLE Reservation (
    Reservation_ID INT PRIMARY KEY,
    Rental_Period INT,
    Return_Status VARCHAR(20),
    Date DATE,
    Equipment_ID INT,
    Student_ID INT,
    FOREIGN KEY (Equipment_ID) REFERENCES Equipment(Equipment_ID),
    FOREIGN KEY (Student_ID) REFERENCES Student(Student_ID)
);

-- Rental Table
CREATE TABLE Rental (
    Rental_ID INT PRIMARY KEY,
    Rental_Date DATE,
    Return_Date DATE,
    Damage_Report VARCHAR(255),
    Student_ID INT,
    Equipment_ID INT,
    FOREIGN KEY (Student_ID) REFERENCES Student(Student_ID),
    FOREIGN KEY (Equipment_ID) REFERENCES Equipment(Equipment_ID)
);

-- Sample data insertion
INSERT INTO Admin (Admin_ID, Name, Email, Phone) VALUES 
(1, 'John Doe', 'john@example.com', '123-456-7890'),
(2, 'Jane Smith', 'jane@example.com', '987-654-3210');

INSERT INTO Student (Student_ID, Name, Email, Phone, Overdue_Items, Admin_ID) VALUES 
(1001, 'Alice Brown', 'alice@example.com', '234-567-8901', 0, 1),
(1002, 'Bob Green', 'bob@example.com', '345-678-9012', 1, 1),
(1003, 'Carol White', 'carol@example.com', '456-789-0123', 2, 2),
(1004, 'David Black', 'david@example.com', '567-890-1234', 0, 2),
(1005, 'Eve Blue', 'eve@example.com', '678-901-2345', 1, 1);

INSERT INTO Equipment (Equipment_ID, Name, Type, Status, Maintenance_Status, Admin_ID) VALUES 
(2001, 'Basketball', 'Ball', 'Available', 'Good', 1),
(2002, 'Soccer Ball', 'Ball', 'Available', 'Good', 2),
(2003, 'Tennis Racket', 'Racket', 'In Use', 'Good', 1),
(2004, 'Badminton Shuttle', 'Shuttlecock', 'Available', 'Good', 2),
(2005, 'Volleyball', 'Ball', 'Maintenance', 'Damaged', 1),
(2006, 'Cricket Bat', 'Bat', 'Available', 'Good', 2),
(2007, 'Table Tennis Paddle', 'Paddle', 'In Use', 'Good', 1),
(2008, 'Hockey Stick', 'Stick', 'Available', 'Good', 2);

INSERT INTO Reservation (Reservation_ID, Rental_Period, Return_Status, Date, Equipment_ID, Student_ID) VALUES 
(3001, 7, 'Returned', '2023-10-01', 2001, 1001),
(3002, 3, 'Pending', '2023-10-05', 2002, 1002),
(3003, 10, 'Returned', '2023-09-15', 2003, 1003),
(3004, 5, 'In Progress', '2023-11-01', 2004, 1004),
(3005, 7, 'Returned', '2023-10-20', 2005, 1005),
(3006, 14, 'In Progress', '2023-11-10', 2006, 1001),
(3007, 7, 'Pending', '2023-10-18', 2007, 1002),
(3008, 5, 'Returned', '2023-09-30', 2008, 1003);

INSERT INTO Rental (Rental_ID, Rental_Date, Return_Date, Damage_Report, Student_ID, Equipment_ID) VALUES 
(4001, '2023-10-01', '2023-10-08', 'None', 1001, 2001),
(4002, '2023-10-05', '2023-10-08', 'Minor scratch', 1002, 2002),
(4003, '2023-09-15', '2023-09-25', 'Handle worn', 1003, 2003),
(4004, '2023-11-01', NULL, 'None', 1004, 2004),
(4005, '2023-10-20', '2023-10-27', 'Damaged net', 1005, 2005),
(4006, '2023-11-10', NULL, 'None', 1001, 2006),
(4007, '2023-10-18', NULL, 'Slightly worn', 1002, 2007),
(4008, '2023-09-30', '2023-10-05', 'Good', 1003, 2008);

-- Creating users and granting privileges
-- Create admin user
CREATE USER 'admin_user'@'localhost' IDENTIFIED BY 'admin';

-- Grant all privileges to admin on the entire database
GRANT ALL PRIVILEGES ON sports_rental_db.* TO 'admin_user'@'localhost' WITH GRANT OPTION;

-- Apply the changes
FLUSH PRIVILEGES;

-- Create student user
CREATE USER 'student_user'@'localhost' IDENTIFIED BY 'student';

-- Grant privileges to view equipment and insert into Rental and Reservation tables
GRANT SELECT ON sports_rental.Equipment TO 'student_user'@'localhost';
GRANT UPDATE ON sports_rental.Equipment TO 'student_user'@'localhost';
GRANT SELECT, INSERT ON sports_rental.Rental TO 'student_user'@'localhost';
GRANT SELECT, INSERT ON sports_rental.Reservation TO 'student_user'@'localhost';

-- Apply the changes
FLUSH PRIVILEGES;

-- To make sure Reservation_ID is auto incremented

-- Step 1: Drop the foreign key constraint in Reservation
ALTER TABLE Reservation DROP FOREIGN KEY reservation_ibfk_1;

-- Step 2: Drop the foreign key constraint in Rental
ALTER TABLE Rental DROP FOREIGN KEY rental_ibfk_2;

-- Step 3: Modify Equipment table to make Equipment_ID AUTO_INCREMENT
ALTER TABLE Equipment MODIFY Equipment_ID INT AUTO_INCREMENT;

-- Step 4: Re-add the foreign key constraint in Reservation
ALTER TABLE Reservation 
ADD CONSTRAINT reservation_ibfk_1 
FOREIGN KEY (Equipment_ID) REFERENCES Equipment(Equipment_ID);

-- Step 5: Re-add the foreign key constraint in Rental
ALTER TABLE Rental 
ADD CONSTRAINT rental_ibfk_2 
FOREIGN KEY (Equipment_ID) REFERENCES Equipment(Equipment_ID);

-- Trigger that automatically increments the overdue items when return status becomes Overdue
DELIMITER //

CREATE TRIGGER reservation_create_trigger
AFTER UPDATE ON Reservation
FOR EACH ROW
BEGIN
    IF NEW.Return_Status = 'Overdue' THEN
        UPDATE Student
        SET Overdue_Items = Overdue_Items + 1
        WHERE Student_ID = NEW.Student_ID;
    END IF;
END//   

DELIMITER ;

-- Updates the Status column in the Equipment table based on the current status of the Equipment
DELIMITER //

CREATE PROCEDURE UpdateEquipmentStatus()
BEGIN
    UPDATE Equipment
    SET Status = 
        CASE
            WHEN Equipment.Maintenance_Status = 'Damaged' THEN 'Maintenance'
            WHEN EXISTS (
                SELECT 1 
                FROM Reservation
                WHERE Reservation.Equipment_ID = Equipment.Equipment_ID
                AND Reservation.Return_Status = 'In Progress'
            ) THEN 'In Use'
            ELSE 'Available'
        END;
End//

DELIMITER ;