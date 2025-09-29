document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    console.log('SocketIO initialized, connecting to:', location.protocol + '//' + document.domain + ':' + location.port);

    socket.on('connect', () => {
        console.log('SocketIO connected');
    });

    socket.on('disconnect', () => {
        console.log('SocketIO disconnected');
    });

    // Webcam setup
    const video = document.getElementById('video-feed');
    let stream;
    if (video) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(mediaStream => {
                stream = mediaStream;
                video.srcObject = stream;
                video.play();
                startSendingFrames();
            })
            .catch(err => {
                console.error('Error accessing webcam:', err);
                alert('Could not access webcam: ' + err.message);
            });
    }

    function startSendingFrames() {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const context = canvas.getContext('2d');
        let lastFrameTime = 0;
        const frameInterval = 2000; // Reduce to 0.5 FPS for better performance on slow servers
        let isFrameProcessing = false; // Flag to prevent overlapping frame processing

        function sendFrame(timestamp) {
            if (!video.srcObject) {
                requestAnimationFrame(sendFrame);
                return; // Skip if video stream is not available
            }
            
            // Only send a new frame if we're not processing one and enough time has passed
            if (!isFrameProcessing && timestamp - lastFrameTime >= frameInterval) {
                isFrameProcessing = true;
                try {
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    const frameData = canvas.toDataURL('image/jpeg', 0.5); // Much lower quality for speed
                    socket.emit('video_frame', frameData);
                    lastFrameTime = timestamp;
                } catch (e) {
                    console.error('Error capturing frame:', e);
                } finally {
                    isFrameProcessing = false;
                }
            }
            requestAnimationFrame(sendFrame);
        }
        requestAnimationFrame(sendFrame);
    }

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
        console.log('Generating calendar with attendedDates:', attendedDates);
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

            td.className = '';

            const jsDay = currentDate.getDay();
            const weekday = (jsDay + 6) % 7;

            if (Array.isArray(attendedDates) && attendedDates.includes(dateStr)) {
                td.classList.add('present');
                console.log(`Marked ${dateStr} as present`);
            } else if (currentDate > today) {
                td.classList.add('non-working');
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

    // Debounce utility
    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
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

        // Add elements for department and role
        const recognizedDepartment = document.getElementById('recognized-department');
        const recognizedRole = document.getElementById('recognized-role');

        function showModal(modal) {
            modal.style.display = 'block';
            setTimeout(() => modal.classList.add('show'), 10);
        }

        function hideModal(modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }

        document.querySelector('#history-modal .close').addEventListener('click', () => hideModal(historyModal));
        document.querySelector('#manage-users-modal .close').addEventListener('click', () => hideModal(manageUsersModal));
        document.querySelector('#user-recognition-modal .close').addEventListener('click', () => {
            hideModal(userRecognitionModal);
            recognizedQueue.shift();
            showNextRecognized();
        });
        document.querySelector('#attendance-breakdown-modal .close').addEventListener('click', () => hideModal(attendanceBreakdownModal));

        startBtn.addEventListener('click', debounce(() => {
            fetch('/start_attendance', { method: 'POST' })
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    recognizedQueue = [];
                    lastRecognizedRoll = null;
                })
                .catch(error => console.error('Start Attendance error:', error));
        }, 300));

        stopBtn.addEventListener('click', debounce(() => {
            fetch('/stop_attendance', { method: 'POST' })
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    recognizedQueue = [];
                    lastRecognizedRoll = null;
                    
                    // Clear status indicators
                    const videoFeed = document.getElementById('video-feed');
                    const statusMessage = document.getElementById('status-message');
                    videoFeed.classList.remove('no-face', 'face-detected', 'face-recognized');
                    statusMessage.classList.remove('no-face', 'face-detected', 'face-recognized');
                    statusMessage.style.display = 'none';
                })
                .catch(error => console.error('Stop Attendance error:', error));
        }, 300));

        historyBtn.addEventListener('click', debounce(() => {
            fetch('/history')
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    historyTableBody.innerHTML = '';
                    data.forEach(record => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${record.name}</td>
                            <td>${record.roll_number}</td>
                            <td>${record.time}</td>
                            <td>${record.date}</td>
                        `;
                        historyTableBody.appendChild(tr);
                    });
                    showModal(historyModal);
                })
                .catch(error => console.error('History error:', error));
        }, 300));

        manageUsersBtn.addEventListener('click', debounce(() => {
            fetch('/manage_users_data')
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    usersTableBody.innerHTML = '';
                    data.forEach(user => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
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
                })
                .catch(error => console.error('Manage Users error:', error));
        }, 300));

        usersTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-btn')) {
                const userId = e.target.dataset.id;
                if (confirm('Are you sure you want to delete this user?')) {
                    fetch(`/delete_user/${userId}`, { method: 'DELETE' })
                        .then(response => {
                            if (!response.ok) throw new Error('Network response was not ok');
                            return response.json();
                        })
                        .then(data => {
                            if (data.success) {
                                e.target.parentElement.parentElement.remove();
                                fetch('/users')
                                    .then(resp => resp.json())
                                    .then(data => updateUserList(data));
                            }
                        })
                        .catch(error => console.error('Delete User error:', error));
                }
            }
            if (e.target.classList.contains('details-btn')) {
                const userId = e.target.dataset.id;
                fetch(`/get_user_history?user_id=${userId}`)
                    .then(response => {
                        if (!response.ok) throw new Error('Network response was not ok');
                        return response.json();
                    })
                    .then(userData => {
                        document.getElementById('recognized-name').textContent = userData.name;
                        document.getElementById('recognized-roll').textContent = userData.roll_number;
                        document.getElementById('recognized-department').textContent = userData.department || 'N/A';
                        document.getElementById('recognized-role').textContent = userData.role || 'N/A';
                        document.getElementById('recognized-attendance-percentage').textContent = userData.attendance_percentage;
                        userHistoryTableBody.innerHTML = '';
                        userData.history.forEach(record => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `<td>${record.time}</td><td>${record.date}</td>`;
                            userHistoryTableBody.appendChild(tr);
                        });
                        currentAttendedDates = Array.isArray(userData.attended_dates) ? userData.attended_dates : [];
                        console.log('Updated currentAttendedDates (details):', currentAttendedDates);
                        showModal(userRecognitionModal);
                    })
                    .catch(error => console.error('User History error:', error));
            }
        });

        exportBtn.addEventListener('click', debounce(() => {
            fetch('/export')
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.blob();
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `attendance_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => console.error('Export error:', error));
        }, 300));

        registerUserBtn.addEventListener('click', () => {
            window.location.href = '/register_user';
        });

        fetch('/users')
            .then(response => response.json())
            .then(data => updateUserList(data))
            .catch(error => console.error('Initial Users fetch error:', error));

        let recognizedQueue = [];
        let currentAttendedDates = [];
        let lastRecognizedRoll = null;
        let lastEventTimestamp = 0;
        let currentUserId = null;

        function showNextRecognized() {
            if (recognizedQueue.length === 0) return;
            const data = recognizedQueue[0];
            document.getElementById('recognized-name').textContent = data.name;
            document.getElementById('recognized-roll').textContent = data.roll_number;
            document.getElementById('recognized-department').textContent = data.department || 'N/A';
            document.getElementById('recognized-role').textContent = data.role || 'N/A';
            document.getElementById('recognized-attendance-percentage').textContent = data.attendance_percentage;
            userHistoryTableBody.innerHTML = '';
            data.history.forEach(record => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${record.time}</td><td>${record.date}</td>`;
                userHistoryTableBody.appendChild(tr);
            });
            currentAttendedDates = Array.isArray(data.attended_dates) ? data.attended_dates : [];
            currentUserId = data.user_id || null;
            lastRecognizedRoll = data.roll_number;
        
            tickOverlay.style.display = 'flex';
            setTimeout(() => {
                tickOverlay.style.display = 'none';
                showModal(userRecognitionModal);
            }, 1000);
        }
        
        socket.on('user_recognized', (data) => {
            const now = Date.now();
            data.timestamp = data.timestamp || now;
            if (data.timestamp <= lastEventTimestamp || (now - lastEventTimestamp) < 5000) return;

            if (data.roll_number !== lastRecognizedRoll || recognizedQueue.length === 0) {
                recognizedQueue.push(data);
                lastEventTimestamp = data.timestamp;
                if (recognizedQueue.length === 1) showNextRecognized();
            }
        });

        attendancePercentage.addEventListener('click', debounce(() => {
            if (currentUserId) {
                fetch(`/get_user_history?user_id=${currentUserId}`)
                    .then(response => {
                        if (!response.ok) throw new Error('Network response was not ok');
                        return response.json();
                    })
                    .then(userData => {
                        currentAttendedDates = Array.isArray(userData.attended_dates) ? userData.attended_dates : [];
                        document.getElementById('recognized-name').textContent = userData.name;
                        document.getElementById('recognized-roll').textContent = userData.roll_number;
                        document.getElementById('recognized-department').textContent = userData.department || 'N/A';
                        document.getElementById('recognized-role').textContent = userData.role || 'N/A';
                        document.getElementById('recognized-attendance-percentage').textContent = userData.attendance_percentage;
                        console.log('Fetched currentAttendedDates for calendar:', currentAttendedDates);
                        generateCalendar(currentAttendedDates);
                        showModal(attendanceBreakdownModal);
                    })
                    .catch(error => console.error('Fetch user history for calendar error:', error));
            } else {
                console.log('No user_id available, using currentAttendedDates:', currentAttendedDates);
                generateCalendar(currentAttendedDates);
                showModal(attendanceBreakdownModal);
            }
        }, 300));
    }

    // Register User Page Logic
    const registerForm = document.getElementById('register-form');
    const backBtn = document.getElementById('back-btn');
    const tickOverlay = document.getElementById('tick-overlay');

    if (registerForm && backBtn && video) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frameData = canvas.toDataURL('image/jpeg', 0.8);

            const formData = new FormData(registerForm);
            formData.set('frame', frameData);

            fetch('/register', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    tickOverlay.style.display = 'flex';
                    setTimeout(() => {
                        tickOverlay.style.display = 'none';
                        registerForm.reset();
                        alert('User registered successfully!');
                    }, 1000);
                } else {
                    alert('Registration failed: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Register error:', error);
                alert('Registration failed: ' + error.message);
            });
        });

        backBtn.addEventListener('click', () => {
            window.location.href = '/';
        });
    }

    // Handle recognition status updates
    socket.on('recognition_status', (data) => {
        const videoFeed = document.getElementById('video-feed');
        const statusMessage = document.getElementById('status-message');
        
        // Remove all status classes
        videoFeed.classList.remove('no-face', 'face-detected', 'face-recognized');
        statusMessage.classList.remove('no-face', 'face-detected', 'face-recognized');
        
        // Add appropriate class and show message
        if (data.status) {
            videoFeed.classList.add(data.status);
            statusMessage.classList.add(data.status);
            statusMessage.textContent = data.message;
            statusMessage.style.display = 'block';
            
            // Hide message after 3 seconds if not a persistent state
            if (data.status !== 'face-recognized') {
                setTimeout(() => {
                    statusMessage.style.display = 'none';
                }, 3000);
            }
        }
    });
});