const id = new URLSearchParams(location.search).get("event");

let ev;

async function load() {
    try {
        ev = await API.request("/api/events/" + id);

        document.getElementById("img").src = ev.image;
        document.getElementById("name").textContent = ev.name;
        document.getElementById("cat").textContent = ev.category;
        document.getElementById("desc").textContent = ev.description;
        document.getElementById("date").textContent = ev.event_date;
        document.getElementById("venue").textContent = ev.venue;
        document.getElementById("fee").textContent =
            ev.fee ? "₹" + ev.fee : "Free";

    } catch (error) {
        document.getElementById("name").textContent = error.message;
    }
}


document.getElementById("register").addEventListener("click", async function () {

    const button = document.getElementById("register");
    const message = document.getElementById("msg");

    // Make sure user is logged in
    if (!localStorage.getItem("eventhub_token"))  {
        location.href =
            "login.html?next=" + encodeURIComponent(location.href);
        return;
    }

    button.disabled = true;
    message.textContent = "Creating registration...";

    try {

        // 1. Create registration
        const registration = await API.request(
            "/api/registrations",
            {
                method: "POST",
                body: JSON.stringify({
                    event_id: Number(id)
                })
            }
        );

        console.log("Registration:", registration);


        // 2. Free event
        if (registration.status === "CONFIRMED") {

            message.textContent = "Registration successful!";

            setTimeout(() => {
                location.href = registration.pass_url;
            }, 500);

            return;
        }


        // 3. Paid event → create Razorpay order
        message.textContent = "Opening payment...";

        const order = await API.request(
            "/api/payments/order",
            {
                method: "POST",
                body: JSON.stringify({
                    registration_id: registration.id
                })
            }
        );


        // 4. Open Razorpay
        const razorpay = new Razorpay({

            key: order.key_id,

            amount: order.amount,

            currency: order.currency,

            order_id: order.order_id,

            name: "EventHub",

            description: order.event_name,

            prefill: {
                name: order.name,
                email: order.email
            },

            handler: async function (response) {

                try {

                    message.textContent =
                        "Verifying payment...";

                    // 5. Verify payment on backend
                    const verified = await API.request(
                        "/api/payments/verify",
                        {
                            method: "POST",

                            body: JSON.stringify({
                                registration_id:
                                    registration.id,

                                razorpay_order_id:
                                    response.razorpay_order_id,

                                razorpay_payment_id:
                                    response.razorpay_payment_id,

                                razorpay_signature:
                                    response.razorpay_signature
                            })
                        }
                    );

                    // 6. Open digital pass
                    location.href = verified.pass_url;

                } catch (error) {

                    message.textContent =
                        "Payment verification failed: " +
                        error.message;

                    button.disabled = false;
                }
            },

            modal: {
                ondismiss: function () {
                    message.textContent =
                        "Payment cancelled.";

                    button.disabled = false;
                }
            }
        });

        razorpay.open();

    } catch (error) {

        console.error(error);

        message.textContent = error.message;

        button.disabled = false;
    }
});


load();