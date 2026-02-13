/* Electric - Main JavaScript */

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });
});

// Confirm before destructive actions
document.querySelectorAll('[data-confirm]').forEach(function(element) {
    element.addEventListener('click', function(e) {
        if (!confirm(this.dataset.confirm)) {
            e.preventDefault();
        }
    });
});

// Action card accordion toggle (home page)
function toggleActionCard(action) {
    var card = document.querySelector('[data-action="' + action + '"]');
    if (!card) return;

    var wasOpen = card.classList.contains('open');

    // Close all cards
    document.querySelectorAll('.action-card').forEach(function(c) {
        c.classList.remove('open');
    });

    // Toggle the clicked card
    if (!wasOpen) {
        card.classList.add('open');
        // Focus the first input in the opened card
        var input = card.querySelector('input[type="number"]');
        if (input) {
            setTimeout(function() { input.focus(); }, 100);
        }
    }
}
