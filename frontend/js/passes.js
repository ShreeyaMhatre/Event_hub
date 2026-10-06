(async () => {
    const box = document.getElementById("box");

    if (!localStorage.getItem("eventhub_token")) {
        box.innerHTML = '<p>Please <a href="login.html">login</a>.</p>';
        return;
    }

    try {
        const registrations = await API.request("/api/registrations/my");

        if (!registrations.length) {
            box.innerHTML = "<p>No registrations yet.</p>";
            return;
        }

        box.innerHTML = registrations.map(r => `
            <div class="registration-card">
                <span class="event-category">
                    ${r.event.category}
                </span>

                <h2>${r.event.name}</h2>

                <p>
                    📅 ${r.event.event_date}
                    • 📍 ${r.event.venue}
                </p>

                <p>
                    Status:
                    <strong>${r.status}</strong>
                </p>

                ${
                    r.pass_url
                    ? `<a class="primary-btn" href="${r.pass_url}">
                        View Pass / QR
                       </a>`
                    : r.status === "PENDING"
                    ? `<p>Payment pending.</p>`
                    : ""
                }
            </div>
        `).join("");

    } catch (e) {
        console.error("My Passes error:", e);

        box.innerHTML = `
            <p style="color:red;">
                Failed to load passes: ${e.message}
            </p>
        `;
    }
})();