const citySearchInput = document.getElementById('city-search');
const addCityBtn = document.getElementById('add-city-btn');
const clocksContainer = document.getElementById('clocks-container');

let cities = [
    { name: 'London', timezone: 'Europe/London' },
    { name: 'New York', timezone: 'America/New_York' },
    { name: 'Tokyo', timezone: 'Asia/Tokyo' }
];

const timezones = {
    "new york": "America/New_York",
    "london": "Europe/London",
    "tokyo": "Asia/Tokyo",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "paris": "Europe/Paris",
    "sydney": "Australia/Sydney",
    "beijing": "Asia/Shanghai",
    "dubai": "Asia/Dubai",
    "singapore": "Asia/Singapore"
};


function renderClocks() {
    clocksContainer.innerHTML = '';
    cities.forEach(city => {
        const clockEl = document.createElement('div');
        clockEl.classList.add('clock');

        const cityEl = document.createElement('div');
        cityEl.classList.add('city');
        cityEl.textContent = city.name;

        const timeEl = document.createElement('div');
        timeEl.classList.add('time');

        const dateEl = document.createElement('div');
        dateEl.classList.add('date');

        clockEl.appendChild(cityEl);
        clockEl.appendChild(timeEl);
        clockEl.appendChild(dateEl);
        clocksContainer.appendChild(clockEl);
    });
    updateClocks();
}

function updateClocks() {
    const clockElements = document.querySelectorAll('.clock');
    clockElements.forEach((clockEl, index) => {
        const city = cities[index];
        const timeEl = clockEl.querySelector('.time');
        const dateEl = clockEl.querySelector('.date');

        try {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { timeZone: city.timezone, hour12: true });
            const dateString = now.toLocaleDateString('en-US', { timeZone: city.timezone });

            timeEl.textContent = timeString;
            dateEl.textContent = dateString;
        } catch (error) {
            timeEl.textContent = 'Invalid Timezone';
            dateEl.textContent = '';
        }
    });
}


addCityBtn.addEventListener('click', () => {
    const cityName = citySearchInput.value.trim().toLowerCase();
    if (cityName && timezones[cityName]) {
        if (!cities.some(c => c.name.toLowerCase() === cityName)) {
            cities.push({ name: cityName.charAt(0).toUpperCase() + cityName.slice(1), timezone: timezones[cityName] });
            renderClocks();
        }
        citySearchInput.value = '';
    } else {
        alert('City not found or already added.');
    }
});

renderClocks();
setInterval(updateClocks, 1000);
