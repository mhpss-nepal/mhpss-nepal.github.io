// Nonclinical engineering fixture; not public learning content.
export default {
  "schema_version": 2,
  "module_id": "skill-loop-interface-demo",
  "content_version": "0.1.0",
  "language": "en",
  "translation_source_version": null,
  "title": "ENGINEERING ONLY — nonclinical interface demo",
  "audience": [
    "Engineering reviewers"
  ],
  "objectives": [
    "Explore interface controls without clinical instruction"
  ],
  "scope_limits": [
    "NONCLINICAL. Candidate illustrations are not instructional approval. No Lesson 3 conversion."
  ],
  "prerequisites": [],
  "estimated_minutes": 5,
  "approval": {
    "status": "draft",
    "technical_reviewer": null,
    "language_reviewer": null,
    "approver": null,
    "review_due": null
  },
  "sources": [
    {
      "source_id": "interface-spec",
      "title": "Engineering interface specification only",
      "edition": "2026-10-11",
      "reference": "CONTRACT-AMENDMENTS.md",
      "location": "Private engineering workspace",
      "rights": "Candidate asset reuse for private engineering only; no publication authority"
    }
  ],
  "lessons": [
    {
      "lesson_id": "pfa-03",
      "title": "Lesson 3 IDs — UI fixture only, not a PFA lesson",
      "objective": "Explore interface controls without clinical instruction",
      "estimated_minutes": 5,
      "blocks": [
        {
          "type": "safety",
          "block_id": "pfa-03-boundaries",
          "body": "Engineering only. Do not use this demo as clinical instruction or a certificate.",
          "source_ids": [
            "interface-spec"
          ]
        },
        {
          "type": "example",
          "block_id": "pfa-03-maya-example",
          "body": "Interface sample B: select a tab to reveal its complete panel. This is synthetic UI text.",
          "source_ids": [
            "interface-spec"
          ]
        },
        {
          "type": "text",
          "block_id": "pfa-03-keypoints",
          "body": "Select an interface control. Read its full feedback. You may stop or skip. These sentences are kept together, including this qualification: no clinical meaning is assigned.",
          "source_ids": [
            "interface-spec"
          ]
        },
        {
          "type": "contrast_pair",
          "block_id": "pfa-03-contrast",
          "prompt": "Compare two interface panels, not two clinical actions.",
          "unhelpful": {
            "body": "Interface sample A: this panel is only a tab demonstration.",
            "source_ids": [
              "interface-spec"
            ],
            "scene_id": "L3-S1"
          },
          "helpful": {
            "ref_block_id": "pfa-03-maya-example",
            "scene_id": "L3-S2"
          },
          "source_ids": [
            "interface-spec"
          ]
        },
        {
          "type": "scene_tap",
          "block_id": "pfa-03-spot",
          "scene_id": "L3-S2",
          "instruction": "Explore two measured corner tiles. These are UI regions, not clinical observations.",
          "layout": {
            "min_image_width_px": 280,
            "target_size_px": 44
          },
          "targets": [
            {
              "target_id": "top-left",
              "label": "Top-left 120 by 80 pixel tile",
              "areas": [
                [
                  0,
                  0,
                  0.1,
                  0.1
                ]
              ],
              "explanation": "This interface tile covers pixels x 0–120 and y 0–80. It assigns no meaning to a person.",
              "source_ids": [
                "interface-spec"
              ]
            },
            {
              "target_id": "bottom-right",
              "label": "Bottom-right 120 by 80 pixel tile",
              "areas": [
                [
                  0.9,
                  0.9,
                  1,
                  1
                ]
              ],
              "explanation": "This interface tile covers pixels x 1080–1200 and y 720–800. It assigns no clinical meaning.",
              "source_ids": [
                "interface-spec"
              ]
            }
          ],
          "list_alternative": [
            {
              "target_id": "top-left",
              "text": "Top-left 120 by 80 pixel tile",
              "did": true,
              "why": "This interface tile covers pixels x 0–120 and y 0–80. It assigns no meaning to a person.",
              "source_ids": [
                "interface-spec"
              ]
            },
            {
              "target_id": "bottom-right",
              "text": "Bottom-right 120 by 80 pixel tile",
              "did": true,
              "why": "This interface tile covers pixels x 1080–1200 and y 720–800. It assigns no clinical meaning.",
              "source_ids": [
                "interface-spec"
              ]
            },
            {
              "text": "A third target is configured in the centre.",
              "did": false,
              "why": "Only two corner tiles are configured in this engineering fixture.",
              "source_ids": [
                "interface-spec"
              ]
            }
          ],
          "source_ids": [
            "interface-spec"
          ]
        },
        {
          "type": "buddy_practice",
          "block_id": "pfa-03-buddy",
          "scene_id": "L3-S7",
          "minutes": 2,
          "roles": [
            {
              "role_id": "helper",
              "role": "Control reader",
              "instruction": "Read a fictional interface label."
            },
            {
              "role_id": "person",
              "role": "Fictional participant",
              "instruction": "Use only a made-up interface preference, never a real story.",
              "fictional_only": true
            },
            {
              "role_id": "observer",
              "role": "Interface observer",
              "instruction": "Notice whether a button label is visible."
            }
          ],
          "source_ids": [
            "interface-spec"
          ]
        }
      ],
      "transfer_goals": {
        "prompt": "Choose whether to reuse this entire interface reminder",
        "options_from_block_id": "pfa-03-keypoints"
      },
      "refresher": {
        "question_ids": [
          "pfa-q05"
        ],
        "offsets_days": [
          7,
          30
        ]
      }
    }
  ],
  "questions": [
    {
      "question_id": "pfa-q05",
      "objective": "Explore interface controls without clinical instruction",
      "prompt": "Which control switches an interface panel?",
      "options": [
        {
          "option_id": "a",
          "text": "A tab control",
          "rationale": "Tabs switch panels in this interface demo.",
          "band": "basic"
        },
        {
          "option_id": "b",
          "text": "An illustration background",
          "rationale": "This background does not switch panels.",
          "band": "could_harm"
        },
        {
          "option_id": "c",
          "text": "A keyboard-operated tab",
          "rationale": "This interface also permits keyboard selection.",
          "band": "further"
        }
      ],
      "correct_option_id": "a",
      "source_ids": [
        "interface-spec"
      ]
    }
  ],
  "completion_policy": {
    "mode": "formative_trial",
    "required_lesson_ids": [
      "pfa-03"
    ],
    "pass_percent": null
  },
  "job_aids": [
    {
      "aid_id": "interface-card",
      "title": "ENGINEERING ONLY — interface reminder",
      "body": "Use controls without entering any personal narrative. No clinical advice.",
      "source_ids": [
        "interface-spec"
      ]
    }
  ],
  "open_questions": [
    "Human review, Claude conversion, exact revision audit and release authority remain separate."
  ],
  "scenes": [
    {
      "scene_id": "L3-S1",
      "file": "L3-S1-version-a-hurried-volunteer.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 1200,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "93802604ec400c2b4c027d88e7ad1fc6d8614d9f174ce81b13ce3d0a5eac0686"
    },
    {
      "scene_id": "L3-S2",
      "file": "L3-S2-version-b-maya-quiet-bench.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 1200,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "e43c6b8796b902c154f39c74de8b73bc2f92c9fb6b6943ffb1e348a4fe9582da"
    },
    {
      "scene_id": "L3-S3",
      "file": "L3-S3-q05-shelter-trembling.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 1200,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "9c903dabaf5797e8ca3bd65c70f7d13c489fe4b69fdd07ce05239ca187850204"
    },
    {
      "scene_id": "L3-S4",
      "file": "L3-S4-grasp-approach.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 800,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "f6c6ec8884fc1cbe9d1df70367c517dc7294b4ee8a0dfd8095f8202f4563be55"
    },
    {
      "scene_id": "L3-S5",
      "file": "L3-S5-grasp-ask.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 800,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "393e3b560c3b84d2cd4a1f28833d319fe2e76591a2a2e4231e3a2b9fb237345c"
    },
    {
      "scene_id": "L3-S6",
      "file": "L3-S6-q06-mother-asks.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 1200,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "d5e84a930bf819b2707c294cb4c20b7fb800e870fb58f99ef6cdd63f6a82118c"
    },
    {
      "scene_id": "L3-S7",
      "file": "L3-S7-buddy-roleplay.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 1200,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "90532e53e6a7c630364f5f46c0d3986b912eaf4094f8d1e9002b44f5e6b501d0"
    },
    {
      "scene_id": "L3-S8",
      "file": "L3-S8-carry-pocket-card.webp",
      "asset_version": "pfa-lesson3-scenes-v0.1",
      "width": 800,
      "height": 800,
      "alt": "Candidate illustration used only as an interface canvas, not clinical instruction.",
      "status": "candidate",
      "sha256": "7ee00318e155aa6d9ae0cce0eecd25366321a334eeea11cd455a5d2f45adbbbc"
    }
  ]
}
;
