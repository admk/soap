test_programs = {
    'if': {
        'program': """
            #pragma soap input int x = 0, int n = 1
            #pragma soap output x
            if (x < n) {
                x = x + 1;
            } else {
                x = x - 1;
            }
            """,
        'fusion_count': 0,
        'fusion_vartup_len': 0,
    },
    'while': {
        'program': """
            #pragma soap input int x = 0, int n = 5
            #pragma soap output x
            while (x < n) {
                x = x + 1;
            }
            """,
        'fusion_count': 0,
        'fusion_vartup_len': 0,
    },
    'if_fusion': {
        'program': """
            #pragma soap input int a = [0, 2], int x = 0, int y = 0
            #pragma soap output x, y
            if (a < 1) {
                x = x + 1;
            }
            if (a < 1) {
                y = y - 1;
            }
            """,
        'fusion_count': 1,
        'fusion_vartup_len': 2,
    },
    'while_fusion': {
        'program': """
            #pragma soap input int x = 0, int y = 1, int n = 5
            #pragma soap output x, y
            int k = x;
            while (x < n) {
                x = x + 1;
            }
            x = k;
            while (x < n) {
                y = y * x;
                x = x + 1;
            }
            """,
        'fusion_count': 1,
        'fusion_vartup_len': 2,
    },
    'nested_if': {
        'program': """
            #pragma soap input int x = 0, int y = 0, int a = -1, int b = -1
            #pragma soap output x, y
            if (a < 0) {
                if (b < 0) {
                    x = x + 1;
                }
            }
            if (b < 0) {
                if (a < 0) {
                    y = y - 1;
                }
            }
            """,
        'fusion_count': 1,
        'fusion_vartup_len': 2,
    },
    'nested_while': {
        'program': """
            #pragma soap input int x = 1, int y = 0, int n = 5
            #pragma soap output x, y
            while (x < n) {
                x = x + 1;
                while (y < x) {
                    y = y + 1;
                }
                x = x + y;
            }
            """,
        'fusion_count': 1,
        'fusion_vartup_len': 2,
    },
}
