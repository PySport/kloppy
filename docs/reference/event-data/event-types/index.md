# Event Types

Each event has a type that classifies the general category to which the event belongs. This classification depends on the data provider of the original data. By default, each event in the data provider’s original data is deserialized as a GENERIC event.

<style type="text/css">
.tg  {border-collapse:collapse;border-spacing:0;}
.tg td{border-color:black;border-style:solid;border-width:1px;font-family:Arial, sans-serif;font-size:14px;
  overflow:hidden;padding:10px 5px;word-break:normal;}
.tg th{border-color:black;border-style:solid;border-width:1px;font-family:Arial, sans-serif;font-size:14px;
  font-weight:normal;overflow:hidden;padding:10px 5px;word-break:normal;}
.tg .tg-473x{border-color:inherit;color:#15C;text-align:left;text-decoration:underline;vertical-align:top}
.tg .tg-c01b{background-color:#C27BA0;border-color:inherit;color:#FFF;font-weight:bold;text-align:left;vertical-align:top}
.tg .tg-8xak{background-color:#C27BA0;color:#FFF;font-weight:bold;text-align:left;vertical-align:top}
.tg .tg-0pky{border-color:inherit;text-align:left;vertical-align:top}
.tg .tg-0lax{text-align:left;vertical-align:top}
.parsed {
  background-color: #50C878;
  opacity: 0.8;
  border: none;
  color: white;
  padding: 5px 10px;
  text-align: center;
  text-decoration: none;
  font-size: 0.8em;
  display: inline-block;
  margin: 2px 1px;
  cursor: pointer;
  border-radius: 4px;
}
</style>
<table class="tg">
<thead>
  <tr>
    <th class="tg-c01b"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Value</span></th>
    <th class="tg-c01b"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Value Description</span></th>
    <th class="tg-c01b"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">StatsBomb</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Opta</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Wyscout v2</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Wyscout v3</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">DataFactory</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Sportec</span></th>
    <th class="tg-8xak"><span style="font-weight:700;font-style:normal;text-decoration:none;color:#FFF;background-color:transparent">Metrica (JSON)</span></th>
  </tr>
</thead>
<tbody>
  <tr>
    <td class="tg-0pky"><span style="">GENERIC</span></td>
    <td class="tg-0pky"><span style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">Unrecognised event type</span></td>
    <td class="tg-0pky"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
  </tr>
  <tr>
    <td class="tg-473x"><a href="/reference/event-data/event-types/pass/"><span style="font-weight:400;font-style:normal;text-decoration:underline;color:#15C;background-color:transparent">PASS</span></a></td>
    <td class="tg-0pky"><span style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent" aria-describedby="__tooltip2_11">The attempted delivery of the ball from one player to another player on the same team. </span></td>
    <td class="tg-0pky"><span class="parsed" title="StatsBomb event type 30/'Pass'">Parsed</span></td>
    <td class="tg-0lax"><span class="parsed" title="Opta event type 1/”Pass” or 2/”Offside pass”">Parsed</span></td>
    <td class="tg-0lax"><span class="parsed" title="Wysout event type 8/”Pass” or subtype 30/”Corner”, 31/”Free kick”, 32/”Free kick (cross)”, 34/”Goal kick”, 36/”Throw in”">Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
    <td class="tg-0lax"><span class="parsed"> Parsed</span></td>
  </tr>
</tbody></table>
