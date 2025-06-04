let socket = null;
let userLocation = null;

//async function reverseGeocode(lat, lng) {
  //const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`;
  //const res = await fetch(url);
  //const data = await res.json();
  //return data.display_name || "Unknown location";
//}

function initHomeMap() {
  const mapContainer = document.getElementById("home-map");
  if (!mapContainer || mapContainer._leaflet_id) return;

  if (!navigator.geolocation) {
    alert("อุปกรณ์ของคุณไม่รองรับ Geolocation");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;

      if (typeof lat !== "number" || typeof lng !== "number") {
        console.error("❌ Invalid coordinates received:", lat, lng);
        alert("พิกัดไม่ถูกต้อง กรุณาลองใหม่");
        return;
      }

      userLocation = { latitude: lat, longitude: lng };

      const map = L.map("home-map").setView([lat, lng], 15);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);

      L.marker([lat, lng]).addTo(map)
        .bindPopup("📍 You are here")
        .openPopup();
    },
    (err) => {
      console.error("❌ Failed to get location:", err.message);
      alert("กรุณาเปิดการเข้าถึงตำแหน่งเพื่อใช้งาน SOS");
    }
  );
}

window.initHomeMap = initHomeMap;

window.addEventListener("DOMContentLoaded", () => {
  socket = new WebSocket(`ws://${location.host}/ws/alerts`);

  socket.onopen = () => console.log("✅ WebSocket connected");
  socket.onmessage = (event) => console.log("📩 Message from server:", event.data);
  socket.onerror = (error) => console.error("❗ WebSocket error:", error);
  socket.onclose = () => console.warn("❌ WebSocket closed");

  const sosButton = document.getElementById("sos-button");
  if (sosButton) {
    sosButton.addEventListener("click", async () => {
      if (!userLocation) {
        alert("ตำแหน่งของคุณยังไม่พร้อม กรุณารอสักครู่...");
        return;
      }

      if (socket && socket.readyState === WebSocket.OPEN) {
        const timestamp = new Date().toISOString();
        const lat = userLocation.latitude;
        const lng = userLocation.longitude;
        const locationName = await reverseGeocode(lat, lng);

        const alertData = {
          message: "🚨 SOS Triggered!",
          timestamp,
          location: locationName,
          prediction: "sos",
          confidence: 0.99,
          latitude: lat,
          longitude: lng,
          source: "user"
        };

        socket.send(JSON.stringify(alertData));
        console.log("📤 Sent SOS (WebSocket):", alertData);

        fetch("/api/sos", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(alertData),
        })
        .then((res) => res.json())
        .then((data) => {
          console.log("✅ Saved to DB:", data);
          const statusEl = document.getElementById("sos-status");
          statusEl.textContent = "🚨 SOS alert submitted!";
          setTimeout(() => {
            statusEl.textContent = "";
          }, 5000);
        })
        .catch((err) => console.error("❌ Failed to save to DB:", err));
      } else {
        alert("การเชื่อมต่อยังไม่พร้อม กรุณาลองใหม่");
      }
    });

  }
});
