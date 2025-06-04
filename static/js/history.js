function showNewRealtimeImage(data) {
  const container = document.getElementById("realtime-image-list");

  const wrapper = document.createElement("div");
  wrapper.className = "realtime-image-item";

  const info = document.createElement("p");
  info.innerHTML = `
    <b>Location:</b> ${data.location}<br/>
    <b>Time:</b> ${formatTimestamp(data.timestamp)}<br/>
    <b>Confidence:</b> ${data.confidence}
  `;

  const img = document.createElement("img");
  if (data.image_data) {
    img.src = `data:image/jpeg;base64,${data.image_data}`;
  } else {
    img.src = `/image/${data.raw_id || data._id}`;
  }
  img.alt = "sos image";
  img.width = 300;
  img.onerror = () => {
    img.src = "/static/img/no-image.jpg";
  };

  wrapper.appendChild(info);
  wrapper.appendChild(img);
  container.prepend(wrapper);
}

function formatTimestamp(iso) {
  const local = new Date(iso);
  return local.toLocaleString('en-GB', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
    hour12: false,
  });
}



let historyMap = null;

function appendNewTableRow(data) {
  const tbody = document.querySelector("#history-table tbody");
  const tr = document.createElement("tr");

  const name = data.name || "user";

  let imgSrc = "/static/img/no-image.jpg";
  if (data.image_data || data.raw_id || data._id) {
    imgSrc = `/image/${data.raw_id || data._id}`;
  }

  tr.innerHTML = `
    <td>${formatTimestamp(data.timestamp || "")}</td>
    <td>${data.location || "-"}</td>
    <td>${(typeof data.latitude === 'number' && typeof data.longitude === 'number') 
            ? `${data.latitude.toFixed(5)}, ${data.longitude.toFixed(5)}` : "-"}</td>
    <td>${data.confidence?.toFixed(2) || "-"}</td>
    <td><img src="${imgSrc}" alt="sos image" width="100"
      onerror="this.src='/static/img/no-image.jpg';" /></td>
    <td>${typeof name === 'string' ? name : "user"}</td>
    <td><button class="delete-btn">🗑️</button></td>
  `;

  tr.querySelector(".delete-btn").onclick = async () => {
    if (confirm("Are you sure you want to delete this record?")) {
      await fetch(`/api/history/${data._id}`, { method: "DELETE" });
      tr.remove(); 
    }
  };

  tbody.prepend(tr); 
}


function initHistoryMap(data) {
  if (!Array.isArray(data)) {
    console.error("❌ initHistoryMap: data ไม่ใช่ array หรือ undefined:", data);
    return;
  }

  if (!historyMap) {
    historyMap = L.map("history-map").setView([0, 0], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(historyMap);
  }

  const bounds = [];

  data.forEach(item => {
    if (typeof item.latitude === 'number' && typeof item.longitude === 'number') {
      const marker = L.marker([item.latitude, item.longitude])
        .bindPopup(`<b> ${item.location || "Unknown"}</b><br>${formatTimestamp(item.timestamp)}`);
      marker.addTo(historyMap);
      bounds.push([item.latitude, item.longitude]);
    }
  });

  if (bounds.length > 0) {
    historyMap.fitBounds(bounds, { padding: [20, 20] });
  }
}

async function loadHistory() {
  console.log("📥 loadHistory started");

  try {
    const res = await fetch("/api/all_sos");
    if (!res.ok) throw new Error("Failed to fetch history data");

    const result = await res.json();
    const data = result.data;
    console.log("✅ DEBUG DATA:", data.map(d => [d.name, d.timestamp, d._id]));

    
    data.sort((a, b) => {
      const t1 = new Date(a.timestamp || 0).getTime();
      const t2 = new Date(b.timestamp || 0).getTime();
      return t2 - t1; // มากกว่าอยู่บนสุด (ล่าสุด)
    });
    

    if (!Array.isArray(data) || data.length === 0) return;

    initHistoryMap(data); // แสดง marker บนแผนที่

    const latest = data[0];
    const tbody = document.querySelector("#history-table tbody");
    tbody.innerHTML = "";

    data.forEach(item => {
      const tr = document.createElement("tr");
      const name = item.name || "user";  
    
      let imgSrc = "/static/img/no-image.jpg";
      if (item.image_data || item.raw_id || item._id) {
        imgSrc = `/image/${item.raw_id || item._id}`;
      }

      tr.innerHTML = `
       <td>${formatTimestamp(item.timestamp || "")}</td>
       <td>${item.location || "-"}</td>
       <td>${(typeof item.latitude === 'number' && typeof item.longitude === 'number') 
               ? `${item.latitude.toFixed(5)}, ${item.longitude.toFixed(5)}` : "-"}</td>
       <td>${item.confidence?.toFixed(2) || "-"}</td>
       <td><img src="${imgSrc}" alt="sos image" width="100"
         onerror="this.src='/static/img/no-image.jpg';" /></td>
       <td>${typeof item.name === 'string' ? item.name : "user"}</td>
       <td><button class="delete-btn">🗑️</button></td>
      `;

    
      tr.querySelector(".delete-btn").onclick = async () => {
        if (confirm("Are you sure you want to delete this record?")) {
          await fetch(`/api/history/${item._id}`, { method: "DELETE" });
          loadHistory();
        }
      };
    
      tbody.appendChild(tr);
    });
    

    document.getElementById("latest-time").textContent = latest.timestamp || "-";
    document.getElementById("latest-location").textContent = latest.location || "-";
    document.getElementById("latest-coord").textContent =
      (typeof latest.latitude === 'number' && typeof latest.longitude === 'number')
        ? `${latest.latitude.toFixed(5)}, ${latest.longitude.toFixed(5)}` : "-";
    document.getElementById("latest-confidence").textContent =
      latest.confidence?.toFixed(2) || "-";

    const img = document.getElementById("latest-image");
    img.src = `/image/${latest._id}`;
    img.onerror = () => {
      img.src = "/static/img/no-image.jpg";
    };

  } catch (err) {
    alert("❌ Load History Error: " + err.message);
  }
}

// WebSocket สำหรับข้อมูล formatted_ai_data แบบ realtime
const historySocket = new WebSocket("ws://127.0.0.1:8000/ws/formatted");

historySocket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  console.log("New formatted_ai_data (realtime):", data);
  console.log("image_data preview:", data.image_data?.slice(0, 30));
  console.log("image id:", data._id, "has image_data?", !!data.image_data);

  showNewRealtimeImage(data);  
  appendNewTableRow(data); 

  if (historyMap && typeof data.latitude === 'number' && typeof data.longitude === 'number') {
    const marker = L.marker([data.latitude, data.longitude])
      .bindPopup(`<b> ${data.location || "Unknown"}</b><br>${formatTimestamp(data.timestamp)}`);
    marker.addTo(historyMap);
  }
};

window.loadHistory = loadHistory;
