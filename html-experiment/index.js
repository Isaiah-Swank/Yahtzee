/******************************************************
 *                   GLOBALS & CONSTANTS
 ******************************************************/
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

// Overlay references
const overlay = document.getElementById("overlay");
const overlayContent = document.getElementById("overlayContent");

// Sprite references
const diceImg = document.getElementById("diceSprite");
const cupImg = document.getElementById("cupSprite");

// Canvas dimensions
const WINDOW_WIDTH = canvas.width;
const WINDOW_HEIGHT = canvas.height;

// Colors (in hex or rgba)
const COLOR_GREEN = "#228B22";
const COLOR_BROWN = "#DEB887";
const COLOR_WHITE = "#FFFFFF";
const COLOR_BLACK = "#000000";
const COLOR_RED   = "#FF0000";

// Dice / Gameplay
const NUM_DICE = 5;
const MAX_TURNS = 13;
const MAX_ROLLS_PER_TURN = 2;

// For dice.png: 6 faces in a row. We’ll read actual width on load.
let DICE_FACE_WIDTH  = 64;
let DICE_FACE_HEIGHT = 64;

// For dice-cup.png: 4 frames in a row
let CUP_FRAME_COUNT  = 4;
let CUP_FRAME_WIDTH  = 50;
let CUP_FRAME_HEIGHT = 60;
let CUP_SCALE        = 2.5;

let scaledCupWidth   = 0;
let scaledCupHeight  = 0;

let diceFacesLoaded  = false;
let cupFramesLoaded  = false;

let diceFaces = []; // array of 6 sub-images (offscreen canvases)
let cupFrames = []; // array of 4 sub-images (offscreen canvases)

// Dice positions on the main rolling screen
const dicePositions = [
  { x: 100, y: 250 },
  { x: 250, y: 250 },
  { x: 400, y: 250 },
  { x: 550, y: 250 },
  { x: 700, y: 250 },
];

// Cup position on rolling screen
// We'll place it roughly near the bottom center
let cupX = WINDOW_WIDTH / 2;
let cupY = 400;

// Game State
let numPlayers = 1;
let scoreboards = []; // array of scoreboard objects
let currentRound = 1;
let currentPlayer = 0;

// Turn state
let diceValues = [0, 0, 0, 0, 0];
let diceKept   = [false, false, false, false, false];
let rollsLeft  = MAX_ROLLS_PER_TURN;
let turnEnded  = false;
let gameMode   = "promptPlayers"; // e.g. 'promptPlayers', 'rolling', 'scoreSelection', 'gameOver'
let isAnimating = false;          // to prevent overlapping animations

/******************************************************
 *             LOADING SPRITE SHEETS
 ******************************************************/
diceImg.onload = () => {
  // Once dice.png loads, slice it into 6 faces
  DICE_FACE_WIDTH  = Math.floor(diceImg.width / 6);
  DICE_FACE_HEIGHT = diceImg.height;

  for (let i = 0; i < 6; i++) {
    let c = document.createElement("canvas");
    c.width  = DICE_FACE_WIDTH;
    c.height = DICE_FACE_HEIGHT;
    let cctx = c.getContext("2d");
    cctx.drawImage(
      diceImg,
      i * DICE_FACE_WIDTH, 0,
      DICE_FACE_WIDTH, DICE_FACE_HEIGHT,
      0, 0,
      DICE_FACE_WIDTH, DICE_FACE_HEIGHT
    );
    diceFaces.push(c);
  }
  diceFacesLoaded = true;
};

cupImg.onload = () => {
  CUP_FRAME_WIDTH  = Math.floor(cupImg.width / CUP_FRAME_COUNT);
  CUP_FRAME_HEIGHT = cupImg.height;

  scaledCupWidth   = Math.floor(CUP_FRAME_WIDTH  * CUP_SCALE);
  scaledCupHeight  = Math.floor(CUP_FRAME_HEIGHT * CUP_SCALE);

  for (let i = 0; i < CUP_FRAME_COUNT; i++) {
    let c = document.createElement("canvas");
    c.width  = scaledCupWidth;
    c.height = scaledCupHeight;
    let cctx = c.getContext("2d");

    // Slice out the frame, then scale it
    let tmp = document.createElement("canvas");
    tmp.width  = CUP_FRAME_WIDTH;
    tmp.height = CUP_FRAME_HEIGHT;
    let tmpCtx = tmp.getContext("2d");
    tmpCtx.drawImage(
      cupImg,
      i * CUP_FRAME_WIDTH, 0,
      CUP_FRAME_WIDTH, CUP_FRAME_HEIGHT,
      0, 0,
      CUP_FRAME_WIDTH, CUP_FRAME_HEIGHT
    );

    // Now draw that scaled onto c
    cctx.drawImage(tmp, 0, 0, CUP_FRAME_WIDTH, CUP_FRAME_HEIGHT,
                   0, 0, scaledCupWidth, scaledCupHeight);

    cupFrames.push(c);
  }
  cupFramesLoaded = true;
};

/******************************************************
 *             EVENT LISTENERS
 ******************************************************/
// Handle mouse clicks for toggling kept dice
canvas.addEventListener("mousedown", (e) => {
  if (gameMode === "rolling" && !isAnimating) {
    // Check if user clicked on a die
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    for (let i = 0; i < NUM_DICE; i++) {
      const dx = dicePositions[i].x;
      const dy = dicePositions[i].y;
      if (
        mouseX >= dx &&
        mouseX <= dx + DICE_FACE_WIDTH &&
        mouseY >= dy &&
        mouseY <= dy + DICE_FACE_HEIGHT
      ) {
        diceKept[i] = !diceKept[i];
        break;
      }
    }
  }
});

// Handle keyboard presses
window.addEventListener("keydown", (e) => {
  if (gameMode === "rolling" && !isAnimating) {
    if (e.key === "r" || e.key === "R") {
      if (rollsLeft > 0) {
        // Animate the cup shake (async)
        animateCupShake(diceKept, diceValues);
      }
    } else if (e.key === "e" || e.key === "E") {
      turnEnded = true;
      gameMode = "scoreSelection";
      openScoreSelectionOverlay();
    }
  }
});

/******************************************************
 *             MAIN GAME LOOP (30 FPS)
 ******************************************************/
const FPS = 30;
setInterval(gameLoop, 1000 / FPS);

function gameLoop() {
  ctx.clearRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);

  if (!diceFacesLoaded || !cupFramesLoaded) {
    ctx.fillStyle = COLOR_WHITE;
    ctx.font = "24px sans-serif";
    ctx.fillText("Loading images...", 20, 40);
    return;
  }

  switch (gameMode) {
    case "promptPlayers":
      drawPromptPlayersScreen();
      break;
    case "rolling":
      drawRollingScreen();
      break;
    case "scoreSelection":
      // The overlay handles user choice; just show a background
      ctx.fillStyle = COLOR_BROWN;
      ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);
      break;
    case "gameOver":
      drawGameOverScreen();
      break;
  }
}

/******************************************************
 *       PROMPT FOR NUMBER OF PLAYERS (Overlay)
 ******************************************************/
function showPlayerPromptOverlay() {
  overlayContent.innerHTML = `
    <h2>Select Number of Players (1-9)</h2>
    <div>
      ${[1,2,3,4,5,6,7,8,9].map(n => 
        `<button onclick="setNumberOfPlayers(${n})">${n}</button>`
      ).join(' ')}
    </div>
  `;
  overlay.classList.add("active");
}

window.setNumberOfPlayers = function(n) {
  numPlayers = n;
  overlay.classList.remove("active");
  initScoreboards(numPlayers);

  currentRound = 1;
  currentPlayer = 0;
  beginPlayerTurn();
};

function drawPromptPlayersScreen() {
  ctx.fillStyle = COLOR_BROWN;
  ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);
  // Overlay does the input
}

/******************************************************
 *             SCOREBOARD & INITIALIZATION
 ******************************************************/
function initScoreboards(n) {
  scoreboards = [];
  for (let i = 0; i < n; i++) {
    scoreboards.push({
      ones: null,
      twos: null,
      threes: null,
      fours: null,
      fives: null,
      sixes: null,
      three_of_a_kind: null,
      four_of_a_kind: null,
      full_house: null,
      small_straight: null,
      large_straight: null,
      yahtzee: null,
      chance: null,
    });
  }
}

/******************************************************
 *               ROLLING SCREEN
 ******************************************************/
function beginPlayerTurn() {
  diceValues = [0, 0, 0, 0, 0];
  diceKept   = [false, false, false, false, false];
  rollsLeft  = MAX_ROLLS_PER_TURN;
  turnEnded  = false;

  // Immediate initial roll
  rollDice();
  gameMode = "rolling";
}

function drawRollingScreen() {
  ctx.fillStyle = COLOR_GREEN;
  ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);

  // Instruction box
  const boxW = 600, boxH = 150;
  const boxX = (WINDOW_WIDTH - boxW) / 2;
  const boxY = 20;
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(boxX, boxY, boxW, boxH);
  ctx.strokeStyle = COLOR_BLACK;
  ctx.strokeRect(boxX, boxY, boxW, boxH);

  ctx.fillStyle = COLOR_BLACK;
  ctx.font = "24px sans-serif";
  ctx.fillText(`Player ${currentPlayer+1} - Round ${currentRound} of ${MAX_TURNS}`, boxX + 20, boxY + 40);
  ctx.fillText(`Rolls left: ${rollsLeft}`, boxX + 20, boxY + 70);
  ctx.fillText(`Press [R] to roll, [E] to end turn.`, boxX + 20, boxY + 100);

  // Draw dice
  for (let i = 0; i < NUM_DICE; i++) {
    const val = diceValues[i];
    const dx = dicePositions[i].x;
    const dy = dicePositions[i].y;

    ctx.drawImage(diceFaces[val - 1], dx, dy);

    // If kept, draw red outline
    if (diceKept[i]) {
      ctx.strokeStyle = COLOR_RED;
      ctx.lineWidth = 3;
      ctx.strokeRect(dx, dy, DICE_FACE_WIDTH, DICE_FACE_HEIGHT);
    }
  }
}

/******************************************************
 *                 ACTUAL DICE ROLL
 ******************************************************/
function rollDice() {
  for (let i = 0; i < NUM_DICE; i++) {
    if (!diceKept[i]) {
      diceValues[i] = Math.floor(Math.random() * 6) + 1;
    }
  }
}

/******************************************************
 *        CUP-SHAKING ANIMATION (Similar to Pygame)
 ******************************************************/
async function animateCupShake(diceKept, diceValues) {
  if (isAnimating) return; // prevent overlap
  isAnimating = true;

  // Decrement the available rolls
  rollsLeft--;

  // Original Pygame logic:
  // 1) Move unkept dice into the cup
  // 2) Shake the cup (cycling frames)
  // 3) Roll the unkept dice
  // 4) Move them back out

  // Starting positions and scales for each die
  const startPositions = dicePositions.map(pos => ({ x: pos.x, y: pos.y }));
  const finalPositions = dicePositions.map(pos => ({ x: pos.x, y: pos.y }));
  let diceScales = new Array(NUM_DICE).fill(1.0);

  // Cup reference
  const cupTargetX = cupX - (scaledCupWidth / 2);
  const cupTargetY = cupY - (scaledCupHeight / 2);

  // 1) Move dice in
  const stepsIn = 15;
  for (let step = 1; step <= stepsIn; step++) {
    await new Promise(r => requestAnimationFrame(r));
    let frac = step / stepsIn;

    for (let i = 0; i < NUM_DICE; i++) {
      if (!diceKept[i]) {
        let sx = startPositions[i].x;
        let sy = startPositions[i].y;
        // Move them to the center of the cup area
        let tx = cupX - (DICE_FACE_WIDTH / 2);
        let ty = cupY - (scaledCupHeight / 4); // slightly up inside the cup

        // Interpolate
        let nx = sx + (tx - sx) * frac;
        let ny = sy + (ty - sy) * frac;
        startPositions[i].x = nx;
        startPositions[i].y = ny;

        // Scale from 1.0 down to 0.5
        diceScales[i] = 1.0 - 0.5 * frac;
      }
    }

    drawRollingSceneWithCup(startPositions, diceScales, 0); 
  }

  // 2) Shake the cup for ~36 frames
  const shakeFrames = 36;
  for (let frameIdx = 0; frameIdx < shakeFrames; frameIdx++) {
    await new Promise(r => requestAnimationFrame(r));

    // Pick cup frame
    const cupFrameIndex = frameIdx % CUP_FRAME_COUNT;

    // We skip drawing unkept dice while shaking, or we can keep them hidden
    drawRollingSceneWithCup(startPositions, diceScales, cupFrameIndex, true /*skipUnkept*/);
  }

  // 3) Roll the unkept dice
  rollDice();

  // 4) Move dice back out
  const stepsOut = 15;
  for (let i = 0; i < NUM_DICE; i++) {
    if (!diceKept[i]) {
      // Reset them to inside the cup
      let tx = cupX - (DICE_FACE_WIDTH / 2);
      let ty = cupY - (scaledCupHeight / 4);
      startPositions[i].x = tx;
      startPositions[i].y = ty;
      diceScales[i] = 0.5;
    }
  }

  for (let step = 1; step <= stepsOut; step++) {
    await new Promise(r => requestAnimationFrame(r));
    let frac = step / stepsOut;

    for (let i = 0; i < NUM_DICE; i++) {
      if (!diceKept[i]) {
        // Move from cup to the final positions
        let sx = startPositions[i].x;
        let sy = startPositions[i].y;
        let fx = finalPositions[i].x;
        let fy = finalPositions[i].y;

        let nx = sx + (fx - sx) * frac;
        let ny = sy + (fy - sy) * frac;
        startPositions[i].x = nx;
        startPositions[i].y = ny;

        diceScales[i] = 0.5 + 0.5 * frac; // scale from 0.5 back to 1.0
      }
    }

    drawRollingSceneWithCup(startPositions, diceScales, 0);
  }

  // Done animating
  isAnimating = false;
}

// Helper draw function (similar to the rolling screen, but with custom dice positions/scales)
function drawRollingSceneWithCup(positions, scales, cupFrameIdx, skipUnkept=false) {
  // BG
  ctx.fillStyle = COLOR_GREEN;
  ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);

  // Info box
  const boxW = 600, boxH = 150;
  const boxX = (WINDOW_WIDTH - boxW) / 2;
  const boxY = 20;
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(boxX, boxY, boxW, boxH);
  ctx.strokeStyle = COLOR_BLACK;
  ctx.strokeRect(boxX, boxY, boxW, boxH);

  ctx.fillStyle = COLOR_BLACK;
  ctx.font = "24px sans-serif";
  ctx.fillText(`Player ${currentPlayer+1} - Round ${currentRound} of ${MAX_TURNS}`, boxX+20, boxY+40);
  ctx.fillText(`Rolls left: ${rollsLeft}`, boxX+20, boxY+70);
  ctx.fillText(`Press [R] to roll, [E] to end turn.`, boxX+20, boxY+100);

  // Draw dice
  for (let i = 0; i < NUM_DICE; i++) {
    const val = diceValues[i];
    if (skipUnkept && !diceKept[i]) {
      // skip drawing unkept dice (they're "in the cup")
      continue;
    }
    const dx = positions[i].x;
    const dy = positions[i].y;
    const scale = scales[i];

    // Scale the face
    let w = DICE_FACE_WIDTH * scale;
    let h = DICE_FACE_HEIGHT * scale;

    // Offscreen approach, or just do a direct scale
    // We'll do direct scale with drawImage 9-arg version:
    ctx.drawImage(diceFaces[val - 1], 0, 0, DICE_FACE_WIDTH, DICE_FACE_HEIGHT,
                  dx, dy, w, h);

    // If kept, draw red outline (approx bounding box)
    if (diceKept[i]) {
      ctx.strokeStyle = COLOR_RED;
      ctx.lineWidth = 3;
      ctx.strokeRect(dx, dy, w, h);
    }
  }

  // Draw the cup
  ctx.drawImage(cupFrames[cupFrameIdx], cupX - scaledCupWidth/2, cupY - scaledCupHeight/2);
}

/******************************************************
 *     SCORE SELECTION OVERLAY / LOGIC
 ******************************************************/
function openScoreSelectionOverlay() {
  const possible = calculatePossibleScores(diceValues);
  const sb = scoreboards[currentPlayer];

  const catMap = [
    { key: "ones", label: "Ones" },
    { key: "twos", label: "Twos" },
    { key: "threes", label: "Threes" },
    { key: "fours", label: "Fours" },
    { key: "fives", label: "Fives" },
    { key: "sixes", label: "Sixes" },
    { key: "three_of_a_kind", label: "3 of a Kind" },
    { key: "four_of_a_kind",  label: "4 of a Kind" },
    { key: "full_house",      label: "Full House" },
    { key: "small_straight",  label: "Small Straight" },
    { key: "large_straight",  label: "Large Straight" },
    { key: "yahtzee",         label: "Yahtzee" },
    { key: "chance",          label: "Chance" },
  ];

  let html = `<h2>Player ${currentPlayer+1} - Select Category</h2>`;
  html += `<p>Dice: ${diceValues.join(", ")}</p>`;
  html += `<table style="margin:auto;">`;
  html += `<tr><th>Category</th><th>Score</th><th>Action</th></tr>`;

  for (let catObj of catMap) {
    const cat = catObj.key;
    const label = catObj.label;
    const used = sb[cat] !== null;

    if (used) {
      html += `<tr>
                <td>${label}</td>
                <td>Used (score: ${sb[cat]})</td>
                <td>-</td>
               </tr>`;
    } else {
      const possibleScore = possible[cat];
      html += `<tr>
                <td>${label}</td>
                <td>${possibleScore}</td>
                <td>
                  <button onclick="selectScoreCategory('${cat}', false)">Take Score</button>
                  <button onclick="selectScoreCategory('${cat}', true)">Zero This</button>
                </td>
               </tr>`;
    }
  }

  html += `</table>`;
  overlayContent.innerHTML = html;
  overlay.classList.add("active");
}

window.selectScoreCategory = function(category, forceZero) {
  applyScoreToCategory(category, diceValues, currentPlayer, forceZero);
  overlay.classList.remove("active");

  nextPlayerOrRound();
};

function calculatePossibleScores(vals) {
  const counts = {};
  for (let v of vals) {
    counts[v] = (counts[v] || 0) + 1;
  }

  let scoreDict = {
    ones:   sumIfMatch(vals, 1),
    twos:   sumIfMatch(vals, 2),
    threes: sumIfMatch(vals, 3),
    fours:  sumIfMatch(vals, 4),
    fives:  sumIfMatch(vals, 5),
    sixes:  sumIfMatch(vals, 6),
  };

  let has3 = Object.values(counts).some(c => c >= 3);
  scoreDict["three_of_a_kind"] = has3 ? sumAll(vals) : 0;

  let has4 = Object.values(counts).some(c => c >= 4);
  scoreDict["four_of_a_kind"] = has4 ? sumAll(vals) : 0;

  let countVals = Object.values(counts).sort();
  // Strict check for 2 and 3
  let isFullHouse = (Object.keys(counts).length === 2 && countVals[0] === 2 && countVals[1] === 3);
  scoreDict["full_house"] = isFullHouse ? 25 : 0;

  // small straight
  let uniqueVals = [...new Set(vals)].sort();
  let smallStraights = [
    [1,2,3,4],
    [2,3,4,5],
    [3,4,5,6]
  ];
  let hasSmall = smallStraights.some(seq => seq.every(x => uniqueVals.includes(x)));
  scoreDict["small_straight"] = hasSmall ? 30 : 0;

  // large straight
  let largeStraights = [
    [1,2,3,4,5],
    [2,3,4,5,6]
  ];
  let hasLarge = largeStraights.some(seq =>
    seq.length === uniqueVals.length &&
    seq.every(x => uniqueVals.includes(x))
  );
  scoreDict["large_straight"] = hasLarge ? 40 : 0;

  // yahtzee
  let has5 = Object.values(counts).some(c => c === 5);
  scoreDict["yahtzee"] = has5 ? 50 : 0;

  // chance
  scoreDict["chance"] = sumAll(vals);

  return scoreDict;
}

function applyScoreToCategory(cat, vals, playerIdx, forceZero) {
  if (forceZero) {
    scoreboards[playerIdx][cat] = 0;
  } else {
    let possible = calculatePossibleScores(vals);
    scoreboards[playerIdx][cat] = possible[cat];
  }
}

function sumIfMatch(vals, num) {
  return vals.filter(v => v === num).reduce((a,b)=>a+b,0);
}
function sumAll(vals) {
  return vals.reduce((a,b)=>a+b,0);
}

function nextPlayerOrRound() {
  currentPlayer++;
  if (currentPlayer >= numPlayers) {
    currentPlayer = 0;
    currentRound++;
  }

  if (currentRound > MAX_TURNS) {
    gameMode = "gameOver";
    return;
  }

  beginPlayerTurn();
}

/******************************************************
 *          GAME OVER + FINAL SCORES
 ******************************************************/
function drawGameOverScreen() {
  ctx.fillStyle = COLOR_BROWN;
  ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);

  openFinalScoresOverlay();
}

function openFinalScoresOverlay() {
  if (!overlay.classList.contains("active")) {
    let html = `<h2>Game Over!</h2>`;
    html += `<table style="margin:auto;">`;
    html += `<tr><th>Player</th><th>Upper</th><th>Bonus</th><th>Lower</th><th>Total</th></tr>`;

    for (let p = 0; p < numPlayers; p++) {
      let [up, bonus, low, total] = calculateFinalScore(scoreboards[p]);
      html += `<tr>
                <td>P${p+1}</td>
                <td>${up}</td>
                <td>${bonus}</td>
                <td>${low}</td>
                <td>${total}</td>
               </tr>`;
    }
    html += `</table>`;
    html += `<button onclick="restartGame()">Play Again</button>`;
    overlayContent.innerHTML = html;
    overlay.classList.add("active");
  }
}

function calculateFinalScore(sb) {
  let upperKeys = ["ones", "twos", "threes", "fours", "fives", "sixes"];
  let lowerKeys = ["three_of_a_kind", "four_of_a_kind", "full_house",
                   "small_straight", "large_straight", "yahtzee", "chance"];

  let upperScore = 0;
  for (let k of upperKeys) {
    if (sb[k] !== null) upperScore += sb[k];
  }
  let lowerScore = 0;
  for (let k of lowerKeys) {
    if (sb[k] !== null) lowerScore += sb[k];
  }
  let bonus = (upperScore >= 63) ? 35 : 0;
  let total = upperScore + bonus + lowerScore;
  return [upperScore, bonus, lowerScore, total];
}

window.restartGame = function() {
  overlay.classList.remove("active");
  gameMode = "promptPlayers";
  showPlayerPromptOverlay();
};

/******************************************************
 *                 INITIAL STARTUP
 ******************************************************/
// Show the overlay to pick how many players
showPlayerPromptOverlay();
