#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <bitset>
#include <sstream>
#include <algorithm>
#include <limits>

using namespace std;

string round_keys[16];

string hex_to_bin(string hex) {
    string bin = "";
    for (char const &c: hex) {
        switch (toupper(c)) {
            case '0': bin += "0000"; break;
            case '1': bin += "0001"; break;
            case '2': bin += "0010"; break;
            case '3': bin += "0011"; break;
            case '4': bin += "0100"; break;
            case '5': bin += "0101"; break;
            case '6': bin += "0110"; break;
            case '7': bin += "0111"; break;
            case '8': bin += "1000"; break;
            case '9': bin += "1001"; break;
            case 'A': bin += "1010"; break;
            case 'B': bin += "1011"; break;
            case 'C': bin += "1100"; break;
            case 'D': bin += "1101"; break;
            case 'E': bin += "1110"; break;
            case 'F': bin += "1111"; break;
            default: continue;
        }
    }
    return bin;
}

string str_to_bin(string text) {
    string bin = "";
    for (char const &c: text) {
        bin += bitset<8>(c).to_string();
    }
    return bin;
}

string bin_to_hex(string bin) {
    string hex = "";
	if (bin.length() % 4 != 0) {
		bin.insert(0, 4 - (bin.length() % 4), '0');
	}
    for (size_t i = 0; i < bin.length(); i += 4) {
        bitset<4> bits(bin.substr(i, 4));
        stringstream ss;
        ss << std::hex << bits.to_ulong();
        hex += ss.str();
    }
    transform(hex.begin(), hex.end(), hex.begin(), ::toupper);
    return hex;
}

string bin_to_str(string bin) {
    string text = "";
    stringstream sstream(bin);
    while (sstream.good()) {
        bitset<8> bits;
        sstream >> bits;
        if (bits.to_ulong() != 0) {
            text += char(bits.to_ulong());
        }
    }
    return text;
}


string dec_to_bin4(int dec) {
    string bin;
    while (dec != 0) {
        bin = (dec % 2 == 0 ? "0" : "1") + bin;
        dec = dec / 2;
    }
    while (bin.length() < 4) {
        bin = "0" + bin;
    }
    return bin;
}

int bin_to_dec(string bin) {
    int dec = 0;
    int p = 0;
    int size = bin.length();
    for (int i = size - 1; i >= 0; i--) {
        if (bin[i] == '1') {
            dec += pow(2, p);
        }
        p++;
    }
    return dec;
}

string shift_l1(string chunk) {
    string res = "";
    for (int i = 1; i < 28; i++) {
        res += chunk[i];
    }
    res += chunk[0];
    return res;
}

string shift_l2(string chunk) {
    string res = "";
    for (int i = 0; i < 2; i++) {
        for (int j = 1; j < 28; j++) {
            res += chunk[j];
        }
        res += chunk[0];
        chunk = res;
        res = "";
    }
    return chunk;
}

string Xor(string a, string b) {
    string res = "";
    for (size_t i = 0; i < b.size(); i++) {
        res += (a[i] != b[i]) ? "1" : "0";
    }
    return res;
}

void gen_keys(string key) {
    int PC1[56] = {
        57,49,41,33,25,17,9,1,58,50,42,34,26,18,
        10,2,59,51,43,35,27,19,11,3,60,52,44,36,
        63,55,47,39,31,23,15,7,62,54,46,38,30,22,
        14,6,61,53,45,37,29,21,13,5,28,20,12,4
    };
    int PC2[48] = {
        14,17,11,24,1,5,3,28,15,6,21,10,
        23,19,12,4,26,8,16,7,27,20,13,2,
        41,52,31,37,47,55,30,40,51,45,33,48,
        44,49,39,56,34,53,46,42,50,36,29,32
    };
    string pkey = "";
    for (int i = 0; i < 56; i++) {
        pkey += key[PC1[i] - 1];
    }
    string L = pkey.substr(0, 28);
    string R = pkey.substr(28, 28);
    for (int i = 0; i < 16; i++) {
        if (i == 0 || i == 1 || i == 8 || i == 15) {
            L = shift_l1(L);
            R = shift_l1(R);
        } else {
            L = shift_l2(L);
            R = shift_l2(R);
        }
        string comb_key = L + R;
        string rkey = "";
        for (int j = 0; j < 48; j++) {
            rkey += comb_key[PC2[j] - 1];
        }
        round_keys[i] = rkey;
    }
}

string DES(string block, bool encrypt) {
    int IP[64] = {
        58,50,42,34,26,18,10,2,60,52,44,36,28,20,12,4,
        62,54,46,38,30,22,14,6,64,56,48,40,32,24,16,8,
        57,49,41,33,25,17,9,1,59,51,43,35,27,19,11,3,
        61,53,45,37,29,21,13,5,63,55,47,39,31,23,15,7
    };
    int E[48] = {
        32,1,2,3,4,5,4,5,6,7,8,9,8,9,10,11,
        12,13,12,13,14,15,16,17,16,17,18,19,20,21,
        20,21,22,23,24,25,24,25,26,27,28,29,28,29,
        30,31,32,1
    };
    int S_BOX[8][4][16] = {
        {{14,4,13,1,2,15,11,8,3,10,6,12,5,9,0,7},{0,15,7,4,14,2,13,1,10,6,12,11,9,5,3,8},{4,1,14,8,13,6,2,11,15,12,9,7,3,10,5,0},{15,12,8,2,4,9,1,7,5,11,3,14,10,0,6,13}},
        {{15,1,8,14,6,11,3,4,9,7,2,13,12,0,5,10},{3,13,4,7,15,2,8,14,12,0,1,10,6,9,11,5},{0,14,7,11,10,4,13,1,5,8,12,6,9,3,2,15},{13,8,10,1,3,15,4,2,11,6,7,12,0,5,14,9}},
        {{10,0,9,14,6,3,15,5,1,13,12,7,11,4,2,8},{13,7,0,9,3,4,6,10,2,8,5,14,12,11,15,1},{13,6,4,9,8,15,3,0,11,1,2,12,5,10,14,7},{1,10,13,0,6,9,8,7,4,15,14,3,11,5,2,12}},
        {{7,13,14,3,0,6,9,10,1,2,8,5,11,12,4,15},{13,8,11,5,6,15,0,3,4,7,2,12,1,10,14,9},{10,6,9,0,12,11,7,13,15,1,3,14,5,2,8,4},{3,15,0,6,10,1,13,8,9,4,5,11,12,7,2,14}},
        {{2,12,4,1,7,10,11,6,8,5,3,15,13,0,14,9},{14,11,2,12,4,7,13,1,5,0,15,10,3,9,8,6},{4,2,1,11,10,13,7,8,15,9,12,5,6,3,0,14},{11,8,12,7,1,14,2,13,6,15,0,9,10,4,5,3}},
        {{12,1,10,15,9,2,6,8,0,13,3,4,14,7,5,11},{10,15,4,2,7,12,9,5,6,1,13,14,0,11,3,8},{9,14,15,5,2,8,12,3,7,0,4,10,1,13,11,6},{4,3,2,12,9,5,15,10,11,14,1,7,6,0,8,13}},
        {{4,11,2,14,15,0,8,13,3,12,9,7,5,10,6,1},{13,0,11,7,4,9,1,10,14,3,5,12,2,15,8,6},{1,4,11,13,12,3,7,14,10,15,6,8,0,5,9,2},{6,11,13,8,1,4,10,7,9,5,0,15,14,2,3,12}},
        {{13,2,8,4,6,15,11,1,10,9,3,14,5,0,12,7},{1,15,13,8,10,3,7,4,12,5,6,11,0,14,9,2},{7,11,4,1,9,12,14,2,0,6,10,13,15,3,5,8},{2,1,14,7,4,10,8,13,15,12,9,0,3,5,6,11}}
    };
    int P[32] = {
        16,7,20,21,29,12,28,17,1,15,23,26,5,18,31,10,
        2,8,24,14,32,27,3,9,19,13,30,6,22,11,4,25
    };
    int FP[64] = {
        40,8,48,16,56,24,64,32,39,7,47,15,55,23,63,31,
        38,6,46,14,54,22,62,30,37,5,45,13,53,21,61,29,
        36,4,44,12,52,20,60,28,35,3,43,11,51,19,59,27,
        34,2,42,10,50,18,58,26,33,1,41,9,49,17,57,25
    };

    string p1 = "";
    for (int i = 0; i < 64; i++) {
        p1 += block[IP[i] - 1];
    }
    string L = p1.substr(0, 32);
    string R = p1.substr(32, 32);
    for (int i = 0; i < 16; i++) {
        string exp_R = "";
        for (int j = 0; j < 48; j++) {
            exp_R += R[E[j] - 1];
        }
        
        string rkey = encrypt ? round_keys[i] : round_keys[15 - i];
        string xored = Xor(rkey, exp_R);
        
        string sbox_res = "";
        for (int j = 0; j < 8; j++) {
            string row_str = xored.substr(j * 6, 1) + xored.substr(j * 6 + 5, 1);
            int row = bin_to_dec(row_str);
            string col_str = xored.substr(j * 6 + 1, 4);
            int col = bin_to_dec(col_str);
            sbox_res += dec_to_bin4(S_BOX[j][row][col]);
        }
        string p2 = "";
        for (int j = 0; j < 32; j++) {
            p2 += sbox_res[P[j] - 1];
        }
        xored = Xor(p2, L);
        L = R;
        R = xored;
    }
    string final_block = R + L;
    string result = "";
    for (int i = 0; i < 64; i++) {
        result += final_block[FP[i] - 1];
    }
    return result;
}

string get_input(const string& name) {
    string in, bin_in;
    int type;

    cout << "\n--- Masukkan " << name << " ---" << endl;
    cout << "\nPilih tipe input (1=Teks, 2=Hex, 3=Biner): ";
    cin >> type;
    
    cout << "\nMasukkan data: ";
    cin.ignore(numeric_limits<streamsize>::max(), '\n');
    getline(cin, in);

    switch(type) {
        case 1: bin_in = str_to_bin(in); break;
        case 2: bin_in = hex_to_bin(in); break;
        case 3: bin_in = in; break;
        default: bin_in = str_to_bin(in); break;
    }
    return bin_in;
}

int main() {
    string key = get_input("Key");
    string pt = get_input("Plaintext");

    if (key.length() != 64) {
        cout << "\nKey harus 64 bit!" << endl;
        return 1;
    }
    
    if (pt.length() % 8 != 0) {
        cout << "\nPlaintext harus kelipatan 8 bit!" << endl;
        return 1;
    }

    gen_keys(key);

    int og_len = pt.length();
    if (og_len % 64 != 0) {
        pt.append(64 - (og_len % 64), '0');
    }

    string ct = "";
    for (size_t i = 0; i < pt.length(); i += 64) {
        ct += DES(pt.substr(i, 64), true);
    }
    
    cout << "\n--- HASIL ENKRIPSI ---" << endl;
    cout << "Teks: " << bin_to_str(ct) << endl;
    cout << "Hex : " << bin_to_hex(ct) << endl;

    string dt = "";
    for (size_t i = 0; i < ct.length(); i += 64) {
        dt += DES(ct.substr(i, 64), false);
    }
    
    dt = dt.substr(0, og_len);

    cout << "\n--- HASIL DEKRIPSI ---" << endl;
    cout << "Teks: " << bin_to_str(dt) << endl;
    cout << "Hex : " << bin_to_hex(dt) << endl;

    return 0;
}