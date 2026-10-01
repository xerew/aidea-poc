// Report playback of an embedded video as
// { type: 'play'|'pause'|'seek'|'ended'|'time', position, duration, from?, to? }.
// Each tracker returns a function that stops reporting.

const SEEK_JUMP_S = 2

let youTubeReady = null
function loadYouTube() {
  if (!youTubeReady) {
    youTubeReady = new Promise((resolve) => {
      if (window.YT?.Player) { resolve(window.YT); return }
      const previous = window.onYouTubeIframeAPIReady
      window.onYouTubeIframeAPIReady = () => { previous?.(); resolve(window.YT) }
      const script = document.createElement('script')
      script.src = 'https://www.youtube.com/iframe_api'
      script.async = true
      document.head.appendChild(script)
    })
  }
  return youTubeReady
}

let vimeoReady = null
function loadVimeo() {
  if (!vimeoReady) {
    vimeoReady = new Promise((resolve, reject) => {
      if (window.Vimeo?.Player) { resolve(window.Vimeo); return }
      const script = document.createElement('script')
      script.src = 'https://player.vimeo.com/api/player.js'
      script.async = true
      script.onload = () => resolve(window.Vimeo)
      script.onerror = reject
      document.head.appendChild(script)
    })
  }
  return vimeoReady
}

export function trackFileVideo(video, emit) {
  let last = 0
  const state = () => ({
    position: video.currentTime,
    duration: Number.isFinite(video.duration) ? video.duration : 0,
  })
  const handlers = {
    play: () => emit({ type: 'play', ...state() }),
    pause: () => { if (!video.ended) emit({ type: 'pause', ...state() }) },
    seeked: () => { const s = state(); emit({ type: 'seek', from: last, to: s.position, ...s }); last = s.position },
    ended: () => emit({ type: 'ended', ...state() }),
    timeupdate: () => {
      if (video.seeking) return
      const s = state()
      last = s.position
      emit({ type: 'time', ...s })
    },
  }
  Object.entries(handlers).forEach(([name, fn]) => video.addEventListener(name, fn))
  return () => Object.entries(handlers).forEach(([name, fn]) => video.removeEventListener(name, fn))
}

export function trackYouTube(iframe, emit) {
  let player = null
  let timer = null
  let last = 0
  let stopped = false
  const state = () => ({ position: player.getCurrentTime(), duration: player.getDuration() })
  const poll = () => {
    const s = state()
    if (s.position < last || s.position - last > SEEK_JUMP_S + 1) emit({ type: 'seek', from: last, to: s.position, ...s })
    else emit({ type: 'time', ...s })
    last = s.position
  }
  const onStateChange = ({ data }) => {
    if (stopped) return
    const { PLAYING, PAUSED, ENDED } = window.YT.PlayerState
    const s = state()
    clearInterval(timer)
    if (data === PLAYING) {
      if (Math.abs(s.position - last) > SEEK_JUMP_S) emit({ type: 'seek', from: last, to: s.position, ...s })
      emit({ type: 'play', ...s })
      last = s.position
      timer = setInterval(poll, 1000)
    } else if (data === PAUSED) {
      emit({ type: 'pause', ...s })
      last = s.position
    } else if (data === ENDED) {
      emit({ type: 'ended', ...s })
      last = s.position
    }
  }
  loadYouTube()
    .then((YT) => { if (!stopped) player = new YT.Player(iframe, { events: { onStateChange } }) })
    .catch(() => {})
  return () => { stopped = true; clearInterval(timer) }
}

export function trackVimeo(iframe, emit) {
  let player = null
  let last = 0
  let seekFrom = null
  let stopped = false
  const handlers = {
    play: (d) => { last = d.seconds; emit({ type: 'play', position: d.seconds, duration: d.duration }) },
    pause: (d) => emit({ type: 'pause', position: d.seconds, duration: d.duration }),
    ended: (d) => emit({ type: 'ended', position: d.seconds, duration: d.duration }),
    seeking: () => { if (seekFrom === null) seekFrom = last },
    seeked: (d) => {
      emit({ type: 'seek', from: seekFrom ?? last, to: d.seconds, position: d.seconds, duration: d.duration })
      seekFrom = null
      last = d.seconds
    },
    timeupdate: (d) => {
      if (seekFrom !== null) return
      last = d.seconds
      emit({ type: 'time', position: d.seconds, duration: d.duration })
    },
  }
  loadVimeo()
    .then((Vimeo) => {
      if (stopped) return
      player = new Vimeo.Player(iframe)
      Object.entries(handlers).forEach(([name, fn]) => player.on(name, fn))
    })
    .catch(() => {})
  return () => {
    stopped = true
    if (player) Object.keys(handlers).forEach(name => player.off(name))
  }
}
