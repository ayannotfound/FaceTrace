// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    console.log('SocketIO initialized, connecting to:', location.protocol + '//' + document.domain + ':' + location.port);

    socket.on('connect', () => {
        console.log('SocketIO connected');
    });

    socket.on('disconnect', () => {
        console.log('SocketIO disconnected');
    });

    // Update user list
    function updateUserList(users) {
        const userList = document.getElementById('user-list');
        if (userList) {
            userList.innerHTML = '';
            users.forEach(user => {
                const li = document.createElement('li');
                li.textContent = `${user.name} (Roll: ${user.roll_number})`;
                userList.appendChild(li);
            });
        }
    }

    // Generate calendar
    function generateCalendar(attendedDates) {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startDay = firstDay.getDay();

        const calendarDiv = document.getElementById('attendance-calendar');
        calendarDiv.innerHTML = '';

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headerRow = document.createElement('tr');
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        days.forEach(day => {
            const th = document.createElement('th');
            th.textContent = day;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        let tr = document.createElement('tr');
        for (let i = 0; i < startDay; i++) {
            const td = document.createElement('td');
            tr.appendChild(td);
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const currentDate = new Date(year, month, day);
            const td = document.createElement('td');
            td.textContent = day;

            const jsDay = currentDate.getDay();
            const weekday = (jsDay + 6) % 7;

            if (currentDate > today) {
                td.classList.add('non-working');
            } else if (attendedDates.includes(dateStr)) {
                td.classList.add('present');
            } else if (weekday < 5) {
                td.classList.add('absent');
            } else {
                td.classList.add('non-working');
            }

            tr.appendChild(td);
            if ((startDay + day) % 7 === 0 || day === daysInMonth) {
                tbody.appendChild(tr);
                tr = document.createElement('tr');
            }
        }

        table.appendChild(thead);
        table.appendChild(tbody);
        calendarDiv.appendChild(table);
    }

    // Main Page Logic
    const startBtn = document.getElementById('start-attendance-btn');
    if (startBtn) {
        const stopBtn = document.getElementById('stop-attendance-btn');
        const historyBtn = document.getElementById('view-history-btn');
        const exportBtn = document.getElementById('export-attendance-btn');
        const registerUserBtn = document.getElementById('register-user-btn');
        const manageUsersBtn = document.getElementById('manage-users-btn');
        const historyModal = document.getElementById('history-modal');
        const manageUsersModal = document.getElementById('manage-users-modal');
        const userRecognitionModal = document.getElementById('user-recognition-modal');
        const attendanceBreakdownModal = document.getElementById('attendance-breakdown-modal');
        const tickOverlay = document.getElementById('tick-overlay');
        const historyTableBody = document.querySelector('#history-table tbody');
        const usersTableBody = document.querySelector('#users-table tbody');
        const userHistoryTableBody = document.querySelector('#user-history-table tbody');
        const attendancePercentage = document.getElementById('recognized-attendance-percentage');

        // Function to show modal with animation
        function showModal(modal) {
            modal.style.display = 'block';
            setTimeout(() => modal.classList.add('show'), 10);
        }

        // Function to hide modal with animation
        function hideModal(modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }

        // Close Modals - Specific to each modal
        document.querySelector('#history-modal .close').addEventListener('click', () => {
            hideModal(historyModal);
        });
        document.querySelector('#manage-users-modal .close').addEventListener('click', () => {
            hideModal(manageUsersModal);
        });
        document.querySelector('#user-recognition-modal .close').addEventListener('click', () => {
            hideModal(userRecognitionModal);
            recognizedQueue.shift(); // Remove current user
            showNextRecognized();
        });
        document.querySelector('#attendance-breakdown-modal .close').addEventListener('click', () => {
            hideModal(attendanceBreakdownModal);
        });

        // Start Attendance
        startBtn.addEventListener('click', () => {
            fetch('/start_attendance', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.message.includes("Camera not available")) {
                        alert(data.message);
                    } else {
                        startBtn.disabled = true;
                        stopBtn.disabled = false;
                        recognizedQueue = [];
                        lastRecognizedRoll = null;
                        console.log('Attendance started, queue and lastRecognizedRoll reset');
                    }
                });
        });

        // Stop Attendance
        stopBtn.addEventListener('click', () => {
            fetch('/stop_attendance', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    recognizedQueue = [];
                    lastRecognizedRoll = null;
                    console.log('Attendance stopped, queue and lastRecognizedRoll cleared');
                });
        });

        // View History
        historyBtn.addEventListener('click', () => {
            fetch('/history')
                .then(response => response.json())
                .then(data => {
                    historyTableBody.innerHTML = '';
                    data.forEach(record => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${record.id}</td>
                            <td>${record.name}</td>
                            <td>${record.roll_number}</td>
                            <td>${record.time}</td>
                            <td>${record.date}</td>
                        `;
                        historyTableBody.appendChild(tr);
                    });
                    showModal(historyModal);
                });
        });

        // Manage Users
        manageUsersBtn.addEventListener('click', () => {
            fetch('/manage_users_data')
                .then(response => response.json())
                .then(data => {
                    usersTableBody.innerHTML = '';
                    data.forEach(user => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${user.id}</td>
                            <td>${user.name}</td>
                            <td>${user.roll_number}</td>
                            <td>
                                <button class="details-btn" data-id="${user.id}">Details</button>
                                <button class="delete-btn" data-id="${user.id}">Delete</button>
                            </td>
                        `;
                        usersTableBody.appendChild(tr);
                    });
                    showModal(manageUsersModal);
                });
        });

        // Delete User and Details
        usersTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-btn')) {
                const userId = e.target.dataset.id;
                if (confirm('Are you sure you want to delete this user?')) {
                    fetch(`/delete_user/${userId}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                e.target.parentElement.parentElement.remove();
                                fetch('/users')
                                    .then(response => response.json())
                                    .then(data => updateUserList(data));
                            }
                        });
                }
            }
            if (e.target.classList.contains('details-btn')) {
                const userId = e.target.dataset.id;
                fetch(`/get_user_history?user_id=${userId}`)
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return response.json();
                    })
                    .then(userData => {
                        if (userData.error) throw new Error(userData.error);
                        document.getElementById('recognized-name').textContent = userData.name;
                        document.getElementById('recognized-roll').textContent = userData.roll_number;
                        document.getElementById('recognized-attendance-percentage').textContent = userData.attendance_percentage;
                        userHistoryTableBody.innerHTML = '';
                        userData.history.forEach(record => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${record.time}</td>
                                <td>${record.date}</td>
                            `;
                            userHistoryTableBody.appendChild(tr);
                        });
                        showModal(userRecognitionModal);
                    })
                    .catch(error => {
                        console.error('Error fetching user details:', error);
                        alert('Failed to load user details: ' + error.message);
                    });
            }
        });

        // Export Attendance
        exportBtn.addEventListener('click', () => {
            fetch('/export')
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `attendance_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                });
        });

        // Navigation to Register User
        registerUserBtn.addEventListener('click', () => {
            window.location.href = '/register_user';
        });

        // Initial user list
        fetch('/users')
            .then(response => response.json())
            .then(data => updateUserList(data));

        // Handle user recognition with queue
        let recognizedQueue = [];
        let currentAttendedDates = [];
        let lastRecognizedRoll = null;
        let lastEventTimestamp = 0; // Track timestamp of last processed event

        function showNextRecognized() {
            if (recognizedQueue.length === 0) {
                console.log('Queue empty, no modal to show');
                return;
            }
            const data = recognizedQueue[0];
            document.getElementById('recognized-name').textContent = data.name;
            document.getElementById('recognized-roll').textContent = data.roll_number;
            document.getElementById('recognized-attendance-percentage').textContent = data.attendance_percentage;
            userHistoryTableBody.innerHTML = '';
            data.history.forEach(record => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${record.time}</td>
                    <td>${record.date}</td>
                `;
                userHistoryTableBody.appendChild(tr);
            });
            currentAttendedDates = data.attended_dates;
            lastRecognizedRoll = data.roll_number;

            // Show green tick animation, then modal
            tickOverlay.style.display = 'flex';
            setTimeout(() => {
                tickOverlay.style.display = 'none';
                showModal(userRecognitionModal);
            }, 1000);
        }

        socket.on('user_recognized', (data) => {
            const now = Date.now();
            console.log('Received user_recognized event:', data, 'Timestamp:', now);

            // Add timestamp to data if not present
            data.timestamp = data.timestamp || now;

            // Ignore events older than the last processed event or too frequent
            if (data.timestamp <= lastEventTimestamp || (now - lastEventTimestamp) < 5000) {
                console.log('Ignoring duplicate or stale event:', data);
                return;
            }

            // Only add to queue if it's a new recognition
            if (data.roll_number !== lastRecognizedRoll || recognizedQueue.length === 0) {
                recognizedQueue.push(data);
                lastEventTimestamp = data.timestamp;
                console.log('Added to queue:', data, 'Queue length:', recognizedQueue.length);
                if (recognizedQueue.length === 1) {
                    showNextRecognized();
                }
            } else {
                console.log('Duplicate roll number ignored:', data.roll_number);
            }
        });

        // Show calendar on percentage click
        attendancePercentage.addEventListener('click', () => {
            generateCalendar(currentAttendedDates);
            showModal(attendanceBreakdownModal);
        });
    }

    // Register User Page Logic
    const videoFeed = document.getElementById('video-feed');
    const registerBtn = document.getElementById('register-btn');
    const backBtn = document.getElementById('back-btn');
    const registerForm = document.getElementById('register-form');

    if (videoFeed && registerBtn && backBtn && registerForm) {
        console.log('Register page elements found, initializing...');

        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log('Register form submitted');
            const formData = new FormData(registerForm);
            fetch('/register', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Register response:', data);
                if (data.success) {
                    registerForm.reset();
                    alert('User registered successfully!');
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Register error:', error);
                alert('Registration failed: ' + error);
            });
        });

        backBtn.addEventListener('click', () => {
            console.log('Back button clicked');
            window.location.href = '/';
        });
    } else {
        console.error('Register page elements missing:', {
            videoFeed: !!videoFeed,
            registerBtn: !!registerBtn,
            backBtn: !!backBtn,
            registerForm: !!registerForm
        });
    }
});