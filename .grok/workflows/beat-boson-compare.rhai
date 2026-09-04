let meta = #{
    name: "beat-boson-compare",
    description: "Adversarially compare OpenBoson aspects to Boson ExSim/NetSim",
    phases: [
        #{ title: "Compare", detail: "one skeptic per aspect" },
        #{ title: "Verdict", detail: "fail closed without evidence" },
    ],
    when_to_use: "After an OpenBoson aspect ships, judge whether Boson still wins that aspect.",
};

let verdict_schema = #{
    "type": "object",
    "required": ["aspect", "beats_boson", "reason", "evidence", "gaps"],
    "properties": #{
        "aspect": #{ "type": "string" },
        "beats_boson": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
        "evidence": #{ "type": "string" },
        "gaps": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

fn aspect_prompt(name, gate) {
    let p = "GOAL: Decide if OpenBoson currently beats Boson on this aspect. Fail closed.\n";
    p += "Aspect: ";
    p += name;
    p += "\nGate: ";
    p += gate;
    p += "\nRead the repo with read_file and grep. Do not answer from memory.\n";
    p += "Read docs/superpowers/specs/2026-09-04-beat-boson-bar.md first.\n";
    p += "Set beats_boson true ONLY with file or test evidence you inspected.\n";
    p += "If you did not read code, beats_boson must be false.\n";
    p += "gaps lists remaining work. Empty gaps only after reading the relevant files.\n";
    p
}

let aspects = [
    #{ name: "teach", gate: "Practice Check and exam review show explanations; exam mode silent; no template rationales." },
    #{ name: "believe-dhcp", gate: "PC with no lease cannot ping; ipconfig /renew from pool then ping works." },
    #{ name: "coach", gate: "Home/Stats can start weak-domain practice or a matching gold lab in one click." },
    #{ name: "presence", gate: "First-run plus QSS that does not read as 2012 admin chrome." },
    #{ name: "believe-l2", gate: "PortFast and EtherChannel change ping, not just running-config strings." },
];

let wanted = if args == () { () } else { args.aspect };

phase("Compare");
let jobs = [];
for a in aspects {
    if wanted == () || wanted == a.name {
        jobs.push(#{
            prompt: aspect_prompt(a.name, a.gate),
            label: "boson:" + a.name,
            capability_mode: "read-only",
            output_schema: verdict_schema,
        });
    }
}
if jobs.len() == 0 {
    pause("verification", "Pass args.aspect as teach, believe-dhcp, coach, presence, or believe-l2.");
}
let results = parallel(jobs);

phase("Verdict");
let won = [];
let lost = [];
for r in results {
    if r == () || r.success == false || r.output == () {
        lost.push("unverified (reviewer failed)");
    } else if r.output.beats_boson == true && r.output.evidence != () && r.output.evidence != "" {
        won.push(r.output.aspect);
    } else {
        let g = r.output.aspect;
        g += ": ";
        g += r.output.reason;
        lost.push(g);
    }
}

let report = "";
report += "Beat Boson comparison\nWon: ";
report += won.len().to_string();
report += " Lost: ";
report += lost.len().to_string();
report += "\n";
let path = write_scratch_file("boson-compare.md", report);
complete(#{ path: path, won: won, lost: lost, won_count: won.len(), lost_count: lost.len() });
