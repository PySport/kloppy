Coordinate system options for data loading functionality. 

Reference: `kloppy/domain/models/common.py`

## Kloppy `"kloppy"`
- **Origin:** Top Left
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Ranges from 0 to 1 on both axes, e.g., x-dim: [0, 1] and y-dim: [0, 1]

## Metrica `"metrica"`
- **Origin:** Top Left
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Ranges from 0 to 1 on both axes, e.g., x-dim: [0, 1] and y-dim: [0, 1]

## Tracab `"tracab"`
- **Origin:** Center
- **Vertical Orientation:** Bottom to Top
- **Pitch Dimensions:** Scaled to `self.length` and `self.width` in hundreds with the origin at the center, e.g., x-dim: [-5250, 5250] and y-dim: [-3400, 3400]

## Second Spectrum `"secondspectrum"`
- **Origin:** Center
- **Vertical Orientation:** Bottom to Top
- **Pitch Dimensions:** Defined by `self.length` and `self.width` with the origin at the center, e.g., x-dim: [-52.5, 52.5] and y-dim: [-34, 34]

## Opta `"opta"`
- **Origin:** Bottom Left
- **Vertical Orientation:** Bottom to Top
- **Pitch Dimensions:** Fixed at x-dim: [0, 100] and y-dim [0, 100].

## Sportec `"sportec"`
- **Origin:** Bottom Left
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Defined by `self.length` and `self.width`, e.g., x-dim: [0, 105] and y-dim: [0, 68]

## StatsBomb `"statsbomb"`
- **Origin:** Top Left
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Fixed at 120 x 80 units. So, x-dim: [0, 120], y-dim: [0, 80].

## Wyscout `"wyscout"`
- **Origin:** Top Left
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Fixed at x-dim: [0, 100] and y-dim [0, 100].

## SkillCorner `"skillcorner"`
- **Origin:** Center
- **Vertical Orientation:** Bottom to Top
- **Pitch Dimensions:** Defined by `self.length` and `self.width` with the origin at the center, e.g., x-dim: [-52.5, 52.5] and y-dim: [-34, 34]

## Datafactory `"datafactory"`
- **Origin:** Center
- **Vertical Orientation:** Top to Bottom
- **Pitch Dimensions:** Ranges from -1 to 1 on both axes. So, x-dim: [-1, 1], y-dim: [-1, 1].

## StatsPerform `"statsperform"`
- **Origin:** Bottom Left
- **Vertical Orientation:** Bottom to Top
- **Pitch Dimensions:** Defined by `self.length` and `self.width`, e.g., x-dim: [0, 105] and y-dim: [0, 68]