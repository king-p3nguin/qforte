import qforte
import numpy as np
import copy

def organizer_to_circuit(op_organizer):
    #loop through organizer and build circuit
    operator = qforte.QuantumOperator()

    # for jw_term in op_organizer:

    for coeff, word in op_organizer:
        circ = qforte.QuantumCircuit()
        for letter in word:
            circ.add_gate(qforte.make_gate(letter[0], letter[1], letter[1]))

        operator.add_term(coeff, circ)

    return operator

def get_ucc_jw_organizer(sq_excitations, already_anti_herm=False):

    T_organizer = []

    if (already_anti_herm):
        for sq_term in sq_excitations:
            T_organizer.append( get_single_term_jw_organizer(sq_term) )


    else:
        print('\nsq_excitation: ', sq_excitations)
        for sq_op, amp in sq_excitations:
            # sq_op, amp => (p,q), t_p^q
            # print('sq_term: ', sq_term)

            sq_term = [ sq_op, amp ]
                                                #NOTE: maybe conjigate?
            sq_term_dag = [ sq_op[::-1], -1.0*amp ]

            T_organizer.append( get_single_term_jw_organizer(sq_term) )
            T_organizer.append( get_single_term_jw_organizer(sq_term_dag) )

    T_organizer = combine_like_terms(T_organizer)

    return T_organizer

def combine_like_terms(op_organizer):
    # A very slow implementation, could absolutely be improved
    term_coeff_dict = {}
    combined_op_organizer = []
    threshold = 1.0e-10
    for jw_term in op_organizer:
        for coeff, word in jw_term:
            temp_tup = tuple(word)
            # print('')
            # print('coeff: ', coeff)
            # print('word: ', word)
            if( temp_tup not in term_coeff_dict.keys() ):
                term_coeff_dict[temp_tup] = coeff
            else:
                term_coeff_dict[temp_tup] += coeff

    print('\ndict:\n', term_coeff_dict)

    for word in term_coeff_dict:
        if(np.abs(term_coeff_dict[word]) > threshold):
            combined_op_organizer.append([term_coeff_dict[word],
                                        list(word)])

    print('\nfinal op_organizer:\n', combined_op_organizer)

    return combined_op_organizer

def get_single_term_jw_organizer(sq_term):
    '''
    sq_term => [(p,q), t_p^q]
    '''
    n_creators = int(len(sq_term[0]) / 2)
    sq_ops = sq_term[0]
    sq_coeff = sq_term[1]
    # print('sq_ops: ', sq_ops)
    ### if (sq_term[1] < threshold): optionally don't transform

    ### else:
    '''
    organizer => [[coeff_0, [ ("X", i), ("X", j),  ("X", k), ...  ] ], [...] ...]
    '''
    op_organizer = []


    ### For right side operator (a single anihilator or creator)
    for i, op_idx in enumerate(sq_ops):

        r_op_Xorganizer = []
        r_op_Yorganizer = []
        for j in range(op_idx):
            r_op_Xorganizer.append(("Z", j))
            r_op_Yorganizer.append(("Z", j))

        r_op_Xorganizer.append(("X", op_idx))
        r_op_Yorganizer.append(("Y", op_idx))

        rX_coeff = 0.5

        if(i < n_creators):
        ### is a creation operator use -iY
            rY_coeff = -0.5j
        else:
        ### is an anihilation operaotur, use +iY
            rY_coeff = 0.5j

        r_X_term = [rX_coeff, r_op_Xorganizer]
        r_Y_term = [rY_coeff, r_op_Yorganizer]

        # print('r_X_term: ',r_X_term)
        # print('r_Y_term: ',r_Y_term)

        op_organizer = join_lr_organizers(op_organizer, r_X_term, r_Y_term)

    for i in range(len(op_organizer)):
        op_organizer[i][0] *= sq_coeff

    return op_organizer

def join_lr_organizers(current_op_org, r_op_Xterm, r_op_Yterm):
    if not current_op_org:
        combined_op_org = [r_op_Xterm, r_op_Yterm]

    else:
        combined_op_org = []
        for coeff, word in current_op_org:
            # X term stuff
            combX_coeff = coeff * r_op_Xterm[0]
            combX_word = word + r_op_Xterm[1]
            combined_op_org.append([combX_coeff, combX_word])

            # Y term stuff
            combY_coeff = coeff * r_op_Yterm[0]
            combY_word = word + r_op_Yterm[1]
            combined_op_org.append([combY_coeff, combY_word])

    return pauli_condense(combined_op_org)
    '''return object : [
                       [c_i, [ ('z', qi1), ('x', qi2), ... ] ],
                       [c_j, [ ('y', qj1), ... ] ]
    ] '''

def pauli_condense(pauli_op):

    condensed_op = []

    for current_coeff, current_word in pauli_op:
        # sort the pauli ops by increasing qubit
        word = sorted(current_word, key=lambda factor: factor[1])

        condensed_word = [current_coeff, []]

        contractions = {
            ('X', 'Y'): ( 1.0j, 'Z'),
            ('X', 'Z'): (-1.0j, 'Y'),
            ('Y', 'X'): (-1.0j, 'Z'),
            ('Y', 'Z'): ( 1.0j, 'X'),
            ('Z', 'X'): ( 1.0j, 'Y'),
            ('Z', 'Y'): (-1.0j, 'X'),

            ('X', 'X'): ( 1.0, 'I'),
            ('Y', 'Y'): ( 1.0, 'I'),
            ('Z', 'Z'): ( 1.0, 'I'),

            ('I', 'X'): ( 1.0, 'X'),
            ('I', 'Y'): ( 1.0, 'Y'),
            ('I', 'Z'): ( 1.0, 'Z')
        }

        # loop over the letters and pairwise compare then to simplify
        # (coeff, [ ('sigma', idx), ('sigma', idx), ... ] )
        # will modify coeff and delete/replace tuples from the list

        idx1 = 0

        # print('\n\ncurrent word: ', current_word)
        # print('word: ', word)

        # for i in range(len(word)-1):
        while(idx1 < len(word)):

            # print('idx1: ', idx1)

            current_qubit = word[idx1][1]
            temp_list = []
            condensed_temp_list = []

            idx2 = copy.copy(idx1)

            while(idx2 < len(word) and word[idx2][1] == current_qubit):
                # print('  idx2: ', idx2)
                temp_list.append( (word[idx2][0], word[idx2][1]) )
                idx2 += 1

            # print('temp list: ', temp_list)

            if(len(temp_list) == 1):
                condensed_word[1].append(temp_list[0])
                idx1 += len(temp_list)

            else:
                idx3 = 0
                while(idx3 < len(temp_list)-1):
                    condensed_word[0] *= contractions[ (temp_list[idx3][0], temp_list[idx3+1][0]) ][0]
                    new_letter = contractions[ (temp_list[idx3][0], temp_list[idx3+1][0]) ][1]
                    condensed_temp_list.append((new_letter, current_qubit))
                    idx3 += 1

                # print('condensed temp list: ', condensed_temp_list)

                for letter in condensed_temp_list[0][0]:
                    if(letter != 'I'):
                        # print('appending with letter as: ', letter)
                        condensed_word[1].append((letter, current_qubit))



                idx1 += len(temp_list)

        # print('    condensed_word[1]:\n    ', condensed_word[1])

        condensed_op.append(condensed_word)

    return condensed_op
