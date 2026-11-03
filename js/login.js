// Login page er JS

// 1) Password dekhano / lukano
var passwordInput = document.getElementById('password');
var toggleButton = document.getElementById('togglePassword');
var eyeIcon = document.getElementById('eyeIcon');

toggleButton.addEventListener('click', function () {
    var isHidden = passwordInput.type === 'password';
    passwordInput.type = isHidden ? 'text' : 'password';
    eyeIcon.textContent = isHidden ? 'visibility_off' : 'visibility';
});

// 2) Form submit (ekhon shudhu demo - pore data.js diye check korbo)
var loginForm = document.getElementById('loginForm');

loginForm.addEventListener('submit', function (event) {
    event.preventDefault();           // page reload hote debe na
    window.location.href = 'dashboard.html';
});