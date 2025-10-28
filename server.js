const express = require("express")
const fs = require("fs")
const cors = require("cors")
const bodyParser = require("body-parser")
const dataFile = "./data.json"

const app = express()
app.use(cors())
app.use(bodyParser.json({ limit: "10mb" }))

const SUPER_ADMIN_ID = "6526385624"

function readData() {
  if (!fs.existsSync(dataFile)) {
    const initialData = {
      users: [],
      admins: [
        {
          id: SUPER_ADMIN_ID,
          dubbingName: "Super Admin",
          addedBy: "system",
          addedAt: new Date().toISOString(),
          role: "super_admin",
        },
      ],
      banners: [],
      animes: [],
      ads: [],
      stats: { views: 0, purchases: 0, users: 0, totalRevenue: 0 },
    }
    fs.writeFileSync(dataFile, JSON.stringify(initialData, null, 2))
  }
  return JSON.parse(fs.readFileSync(dataFile))
}

function writeData(d) {
  fs.writeFileSync(dataFile, JSON.stringify(d, null, 2))
}

function isAdmin(userId) {
  const d = readData()
  return d.admins.some((a) => a.id === userId.toString()) || userId.toString() === SUPER_ADMIN_ID
}

function isSuperAdmin(userId) {
  const d = readData()
  const admin = d.admins.find((a) => a.id === userId.toString())
  return userId.toString() === SUPER_ADMIN_ID || (admin && admin.role === "super_admin")
}

// Health check
app.get("/ping", (req, res) => res.json({ ok: true, time: Date.now() }))

// ==================== AUTH ====================
app.post("/register", (req, res) => {
  const { name, email, password } = req.body
  if (!email || !password) return res.status(400).json({ error: "missing_fields" })

  const d = readData()
  if (d.users.find((u) => u.email === email)) return res.status(400).json({ error: "user_exists" })

  const user = {
    id: Date.now().toString(),
    name: name || "User",
    email,
    password,
    balance: 0,
    purchasedAnimes: [],
    createdAt: new Date().toISOString(),
  }

  d.users.push(user)
  d.stats.users = d.users.length
  writeData(d)

  return res.status(201).json({ ok: true, user: { ...user, password: undefined } })
})

app.post("/login", (req, res) => {
  const { email, password } = req.body
  const d = readData()
  const u = d.users.find((x) => x.email === email)

  if (!u) return res.status(404).json({ error: "user_not_found" })
  if (u.password !== password) return res.status(401).json({ error: "invalid_password" })

  return res.json({ ok: true, user: { ...u, password: undefined } })
})

// ==================== ADMIN MANAGEMENT ====================
app.post("/add_admin", (req, res) => {
  const { userId, dubbingName, addedBy } = req.body

  if (!userId || !dubbingName) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()

  // Only super admin can add admins
  if (!isSuperAdmin(addedBy)) {
    return res.status(403).json({ error: "only_super_admin_can_add" })
  }

  // Check if already admin
  if (d.admins.find((a) => a.id === userId.toString())) {
    return res.status(400).json({ error: "already_admin" })
  }

  const newAdmin = {
    id: userId.toString(),
    dubbingName,
    addedBy: addedBy.toString(),
    addedAt: new Date().toISOString(),
    role: "admin",
  }

  d.admins.push(newAdmin)
  writeData(d)

  return res.status(201).json({ ok: true, admin: newAdmin })
})

app.get("/admins", (req, res) => {
  const d = readData()
  return res.json({ ok: true, admins: d.admins })
})

// ==================== BANNERS ====================
app.post("/banner", (req, res) => {
  const { text, imageUrl, addedBy } = req.body

  if (!text || !imageUrl) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()

  // Only super admin can add banners
  if (!isSuperAdmin(addedBy)) {
    return res.status(403).json({ error: "only_super_admin_can_add_banners" })
  }

  const banner = {
    id: Date.now().toString(),
    text,
    imageUrl,
    addedBy: addedBy.toString(),
    createdAt: new Date().toISOString(),
  }

  d.banners.push(banner)
  writeData(d)

  return res.status(201).json({ ok: true, banner })
})

app.get("/banners", (req, res) => {
  const d = readData()
  return res.json({ ok: true, banners: d.banners })
})

// ==================== ADVERTISEMENTS ====================
app.post("/ad", (req, res) => {
  const { title, imageUrl, userId } = req.body

  if (!title || !imageUrl || !userId) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()
  const user = d.users.find((u) => u.id === userId)

  if (!user) {
    return res.status(404).json({ error: "user_not_found" })
  }

  // Check balance (500 som for ad)
  if (user.balance < 500) {
    return res.status(402).json({ error: "insufficient_balance", required: 500, current: user.balance })
  }

  // Deduct payment
  user.balance -= 500

  const ad = {
    id: Date.now().toString(),
    title,
    imageUrl,
    userId,
    views: 0,
    clicks: 0,
    createdAt: new Date().toISOString(),
    active: true,
  }

  d.ads.push(ad)
  d.stats.totalRevenue = (d.stats.totalRevenue || 0) + 500
  writeData(d)

  return res.status(201).json({ ok: true, ad, newBalance: user.balance })
})

app.get("/ads", (req, res) => {
  const d = readData()
  const activeAds = d.ads.filter((ad) => ad.active)
  return res.json({ ok: true, ads: activeAds })
})

app.post("/ad/:id/view", (req, res) => {
  const { id } = req.params
  const d = readData()
  const ad = d.ads.find((a) => a.id === id)

  if (!ad) return res.status(404).json({ error: "ad_not_found" })

  ad.views = (ad.views || 0) + 1
  writeData(d)

  return res.json({ ok: true, views: ad.views })
})

// ==================== ANIMES ====================
app.post("/anime", (req, res) => {
  const { title, genre, desc, price, posterUrl, addedBy } = req.body

  if (!title || !genre || !desc || !price || !posterUrl || !addedBy) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()

  // Check if user is admin
  if (!isAdmin(addedBy)) {
    return res.status(403).json({ error: "not_admin" })
  }

  // Validate price
  if (![2900, 5900].includes(Number(price))) {
    return res.status(400).json({ error: "invalid_price", allowed: [2900, 5900] })
  }

  const admin = d.admins.find((a) => a.id === addedBy.toString())

  const anime = {
    id: Date.now().toString(),
    title,
    genre,
    desc,
    price: Number(price),
    posterUrl,
    episodes: [],
    addedBy: addedBy.toString(),
    dubbingName: admin ? admin.dubbingName : "Unknown",
    views: 0,
    purchases: 0,
    revenue: 0,
    createdAt: new Date().toISOString(),
  }

  d.animes.push(anime)
  writeData(d)

  return res.status(201).json({ ok: true, anime })
})

app.get("/animes", (req, res) => {
  const d = readData()
  return res.json({ ok: true, animes: d.animes })
})

app.get("/anime/:id", (req, res) => {
  const { id } = req.params
  const d = readData()
  const anime = d.animes.find((a) => a.id === id)

  if (!anime) return res.status(404).json({ error: "anime_not_found" })

  return res.json({ ok: true, anime })
})

// ==================== EPISODES ====================
app.post("/anime/:id/episode", (req, res) => {
  const { id } = req.params
  const { title, videoUrl, addedBy } = req.body

  if (!title || !videoUrl) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()
  const anime = d.animes.find((a) => a.id === id)

  if (!anime) return res.status(404).json({ error: "anime_not_found" })

  // Check if user is the anime creator or super admin
  if (anime.addedBy !== addedBy.toString() && !isSuperAdmin(addedBy)) {
    return res.status(403).json({ error: "not_authorized" })
  }

  const episode = {
    id: Date.now().toString(),
    title,
    videoUrl,
    views: 0,
    addedAt: new Date().toISOString(),
  }

  anime.episodes.push(episode)
  writeData(d)

  return res.status(201).json({ ok: true, episode, totalEpisodes: anime.episodes.length })
})

// ==================== VIEWS & PURCHASES ====================
app.post("/anime/:id/view", (req, res) => {
  const { id } = req.params
  const { userId } = req.body

  const d = readData()
  const anime = d.animes.find((a) => a.id === id)

  if (!anime) return res.status(404).json({ error: "anime_not_found" })

  anime.views = (anime.views || 0) + 1
  d.stats.views = (d.stats.views || 0) + 1
  writeData(d)

  return res.json({ ok: true, views: anime.views })
})

app.post("/anime/:id/purchase", (req, res) => {
  const { id } = req.params
  const { userId } = req.body

  if (!userId) {
    return res.status(400).json({ error: "missing_user_id" })
  }

  const d = readData()
  const anime = d.animes.find((a) => a.id === id)
  const user = d.users.find((u) => u.id === userId)

  if (!anime) return res.status(404).json({ error: "anime_not_found" })
  if (!user) return res.status(404).json({ error: "user_not_found" })

  // Check if already purchased
  if (user.purchasedAnimes && user.purchasedAnimes.includes(id)) {
    return res.json({ ok: true, alreadyPurchased: true })
  }

  // Check balance
  if (user.balance < anime.price) {
    return res.status(402).json({
      error: "insufficient_balance",
      required: anime.price,
      current: user.balance,
    })
  }

  // Process purchase
  user.balance -= anime.price
  if (!user.purchasedAnimes) user.purchasedAnimes = []
  user.purchasedAnimes.push(id)

  anime.purchases = (anime.purchases || 0) + 1
  anime.revenue = (anime.revenue || 0) + anime.price

  d.stats.purchases = (d.stats.purchases || 0) + 1
  d.stats.totalRevenue = (d.stats.totalRevenue || 0) + anime.price

  writeData(d)

  return res.json({
    ok: true,
    purchased: true,
    newBalance: user.balance,
    anime: anime.title,
  })
})

// ==================== USER BALANCE ====================
app.post("/topup", (req, res) => {
  const { userId, amount } = req.body

  if (!userId || !amount) {
    return res.status(400).json({ error: "missing_fields" })
  }

  const d = readData()
  const user = d.users.find((u) => u.id === userId)

  if (!user) return res.status(404).json({ error: "user_not_found" })

  user.balance = (user.balance || 0) + Number(amount)
  writeData(d)

  return res.json({ ok: true, newBalance: user.balance })
})

app.get("/user/:id/balance", (req, res) => {
  const { id } = req.params
  const d = readData()
  const user = d.users.find((u) => u.id === id)

  if (!user) return res.status(404).json({ error: "user_not_found" })

  return res.json({ ok: true, balance: user.balance, purchasedAnimes: user.purchasedAnimes || [] })
})

// ==================== STATISTICS ====================
app.get("/stats", (req, res) => {
  const d = readData()

  // Calculate admin statistics
  const adminStats = d.admins.map((admin) => {
    const adminAnimes = d.animes.filter((a) => a.addedBy === admin.id)
    const totalViews = adminAnimes.reduce((sum, a) => sum + (a.views || 0), 0)
    const totalPurchases = adminAnimes.reduce((sum, a) => sum + (a.purchases || 0), 0)
    const totalRevenue = adminAnimes.reduce((sum, a) => sum + (a.revenue || 0), 0)

    return {
      id: admin.id,
      dubbingName: admin.dubbingName,
      role: admin.role,
      totalAnimes: adminAnimes.length,
      totalViews,
      totalPurchases,
      totalRevenue,
    }
  })

  // Top animes
  const topAnimes = d.animes
    .sort((a, b) => (b.views || 0) - (a.views || 0))
    .slice(0, 10)
    .map((a) => ({
      id: a.id,
      title: a.title,
      views: a.views || 0,
      purchases: a.purchases || 0,
      revenue: a.revenue || 0,
      dubbingName: a.dubbingName,
    }))

  return res.json({
    ok: true,
    stats: {
      totalUsers: d.users.length,
      totalAnimes: d.animes.length,
      totalBanners: d.banners.length,
      totalAds: d.ads.length,
      totalViews: d.stats.views || 0,
      totalPurchases: d.stats.purchases || 0,
      totalRevenue: d.stats.totalRevenue || 0,
    },
    adminStats,
    topAnimes,
  })
})

// ==================== ADMIN STATS ====================
app.get("/admin/:id/stats", (req, res) => {
  const { id } = req.params
  const d = readData()

  const admin = d.admins.find((a) => a.id === id)
  if (!admin) return res.status(404).json({ error: "admin_not_found" })

  const adminAnimes = d.animes.filter((a) => a.addedBy === id)

  const animeDetails = adminAnimes.map((anime) => ({
    id: anime.id,
    title: anime.title,
    genre: anime.genre,
    price: anime.price,
    views: anime.views || 0,
    purchases: anime.purchases || 0,
    revenue: anime.revenue || 0,
    episodeCount: anime.episodes.length,
    createdAt: anime.createdAt,
  }))

  const totalViews = adminAnimes.reduce((sum, a) => sum + (a.views || 0), 0)
  const totalPurchases = adminAnimes.reduce((sum, a) => sum + (a.purchases || 0), 0)
  const totalRevenue = adminAnimes.reduce((sum, a) => sum + (a.revenue || 0), 0)

  return res.json({
    ok: true,
    admin: {
      id: admin.id,
      dubbingName: admin.dubbingName,
      role: admin.role,
      addedAt: admin.addedAt,
    },
    stats: {
      totalAnimes: adminAnimes.length,
      totalViews,
      totalPurchases,
      totalRevenue,
    },
    animes: animeDetails,
  })
})

const PORT = process.env.PORT || 3000
app.listen(PORT, () => {
  console.log("=================================")
  console.log("🎬 Animelar TV Backend Server")
  console.log("=================================")
  console.log(`🚀 Server running on port ${PORT}`)
  console.log(`👑 Super Admin ID: ${SUPER_ADMIN_ID}`)
  console.log("=================================")
})
