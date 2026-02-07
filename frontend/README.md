# CallPilot Dashboard (Role 3 & 4)

React dashboard for visualizing real-time swarm calls and managing appointment bookings.

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000` and proxy API requests to the Flask backend on `http://localhost:5000`.

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Features

- **Landing Page**: Beautiful hero section with feature highlights
- **Input Form**: Service selection, time window picker, and preference sliders
- **Real-time Swarm Visualization**: Live updates as providers are called
- **Ranked Results**: Smart scoring with detailed breakdowns
- **Booking Confirmation**: Smooth confirmation flow with animations

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   ├── services/         # API services
│   ├── styles/          # Global styles
│   ├── App.jsx          # Main app component
│   └── main.jsx         # Entry point
├── public/              # Static assets
└── package.json         # Dependencies
```

## Integration

The frontend connects to the Flask backend via:
- `/swarm/stream` - Streaming API for real-time updates
- `/data/calendar.json` - Calendar data endpoint
- `/health` - Health check endpoint

Make sure the Flask backend is running on port 5000 before starting the frontend.
