function selectScreen(sources, displayId) {
  const screens = sources.filter(source => source.id.startsWith('screen:'));
  const source = screens.find(source => String(source.display_id) === String(displayId)) || (screens.length === 1 ? screens[0] : null);
  if (!source) throw new Error('Could not identify the current monitor. Move the cursor to the screen you want AIRA to see and retry.');
  return source;
}
module.exports = { selectScreen };
